"""
Flask app that implements the Epistemix API based on the Pact contract.
This app follows Clean Architecture principles with proper separation of concerns.
"""

import logging
import os
from datetime import datetime
from functools import wraps
from typing import List

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError
from returns.pipeline import is_successful

# Import our business models and controllers
from epistemix_platform.controllers.job_controller import JobController
from epistemix_platform.mappers.job_mapper import JobMapper
from epistemix_platform.mappers.run_mapper import RunMapper
from epistemix_platform.models.requests import RegisterJobRequest, SubmitJobRequest, SubmitRunsRequest
from epistemix_platform.repositories.database import get_database_manager
from epistemix_platform.repositories.job_repository import SQLAlchemyJobRepository
from epistemix_platform.repositories.run_repository import SQLAlchemyRunRepository
from epistemix_platform.repositories.s3_upload_location_repository import (
    create_upload_location_repository,
)

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure database
app.config["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:///epistemix_jobs.db")


# Global error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle Pydantic validation errors globally."""
    logger.warning(f"Request validation error: {e}")
    return jsonify({"error": "Invalid request data", "details": e.errors()}), 400


@app.errorhandler(ValueError)
def handle_value_error(e):
    logger.warning(f"Value error: {e}")
    return jsonify({"error": str(e)}), 400


@app.errorhandler(Exception)
def handle_general_exception(e):
    """Handle all other exceptions globally."""
    # Don't log HTTP exceptions (4xx, 5xx) that are intentionally raised
    if hasattr(e, "code") and e.code is not None:
        return e

    logger.error(f"Unexpected error: {e}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.before_request
def before_request():
    """Initialize database session for each request."""
    database_url = app.config["DATABASE_URL"]
    db_manager = get_database_manager(database_url)

    # Ensure tables are created
    db_manager.create_tables()

    g.db_session = db_manager.get_session()


@app.teardown_appcontext
def close_db_session(error):
    """Close database session after each request."""
    db_session = getattr(g, "db_session", None)
    if db_session is not None:
        if error:
            db_session.rollback()
        else:
            try:
                db_session.commit()
            except Exception:
                db_session.rollback()
                raise
        db_session.close()


def get_upload_location_repository():
    """Get the upload location repository based on environment."""
    # Get environment from app config, defaulting to production
    env = app.config.get("ENVIRONMENT", "PRODUCTION")

    # For testing environment, use the dummy repository
    if app.config.get("TESTING", False):
        env = "TESTING"

    # Configure S3 parameters from environment variables
    bucket_name = app.config.get("S3_UPLOAD_BUCKET")
    region_name = app.config.get("AWS_REGION")

    return create_upload_location_repository(
        env=env, bucket_name=bucket_name, region_name=region_name
    )


def get_job_controller():
    """Get a JobController instance with the current request's database session."""

    def session_factory():
        return g.db_session

    # Create mapper instances
    job_mapper = JobMapper()
    run_mapper = RunMapper()
    
    # Create repository instances with injected mappers
    job_repository = SQLAlchemyJobRepository(job_mapper, session_factory)
    run_repository = SQLAlchemyRunRepository(run_mapper, session_factory)
    upload_location_repository = get_upload_location_repository()

    return JobController.create_with_repositories(
        job_repository, run_repository, upload_location_repository
    )


def validate_headers(required_headers: List[str]) -> bool:
    """Validate that required headers are present in the request.
    Performs case-insensitive header name matching.
    """
    # Create a set of lowercase header names from the request
    request_headers_lower = {key.lower() for key in request.headers.keys()}
    
    for header in required_headers:
        if header.lower() not in request_headers_lower:
            return False
    return True


def require_headers(*headers):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not validate_headers(list(headers)):
                return jsonify({"error": "Missing required headers"}), 400

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_json(content_type="application/json"):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate content type with case-insensitive matching and parameter handling
            request_content_type = request.headers.get("content-type") or request.headers.get("Content-Type")
            if not request_content_type:
                return jsonify({"error": f"Content-Type must be {content_type}"}), 400
            
            # Extract the main content type (ignore parameters like charset)
            main_content_type = request_content_type.split(';')[0].strip().lower()
            expected_content_type = content_type.lower()
            
            if main_content_type != expected_content_type:
                return jsonify({"error": f"Content-Type must be {content_type}"}), 400

            # Get and validate JSON data
            raw_data = request.get_json()
            if not raw_data:
                return jsonify({"error": "Invalid JSON"}), 400

            # Pass the JSON data as the first argument to the route function
            return f(raw_data, *args, **kwargs)

        return decorated_function

    return decorator


def inject_user_token():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract the Offline-Token header with case-insensitive matching
            user_token_value = request.headers.get("Offline-Token") or request.headers.get("offline-token")
            if not user_token_value:
                return jsonify({"error": "Missing Offline-Token header"}), 400

            return f(user_token_value, *args, **kwargs)

        return decorated_function

    return decorator


@app.route("/jobs/register", methods=["POST"])
@require_headers("Offline-Token", "content-type", "Fredcli-Version", "user-agent")
@require_json("application/json")
@inject_user_token()
def register_job(user_token_value, json_data):
    """Persists a new job to Epistemix platform."""
    request_data = RegisterJobRequest(**json_data)

    job_controller = get_job_controller()
    job_result = job_controller.register_job(
        user_token_value=user_token_value, tags=request_data.tags
    )

    if not is_successful(job_result):
        error_message = job_result.failure()
        logger.warning(f"Business logic error in job registration: {error_message}")
        return jsonify({"error": error_message}), 400

    job_data = job_result.unwrap()
    job_response = {
        "id": job_data["id"],
        "userId": job_data["userId"],
        "tags": job_data["tags"],
    }

    return jsonify(job_response), 200


@app.route("/jobs", methods=["POST"])
@require_headers("Offline-Token", "content-type", "Fredcli-Version", "user-agent")
@require_json("application/json")
def submit_job(json_data):
    """Submit registered job for processing to Epistemix platform."""
    request_data = SubmitJobRequest(**json_data)

    job_controller = get_job_controller()
    job_submission_result = job_controller.submit_job(
        job_id=request_data.jobId,
        context=request_data.context,
        job_type=request_data.uploadType,
        run_id=request_data.runId,
    )

    if not is_successful(job_submission_result):
        error_message = job_submission_result.failure()
        logger.warning(f"Business logic error in job submission: {error_message}")
        return jsonify({"error": error_message}), 400

    return jsonify(job_submission_result.unwrap()), 200


@app.route("/runs", methods=["POST"])
@require_headers("Offline-Token", "content-type", "Fredcli-Version", "user-agent")
@require_json()
@inject_user_token()
def submit_runs(user_token_value, json_data):
    """
    Submit run requests.
    Implements the run submission interaction from the Pact contract.
    """
    submit_runs_request = SubmitRunsRequest(**json_data)
    run_requests = [run_request.model_dump() for run_request in submit_runs_request.runRequests]

    job_controller = get_job_controller()
    run_submission_result = job_controller.submit_runs(
        run_requests=run_requests, user_token_value=user_token_value
    )

    if not is_successful(run_submission_result):
        error_message = run_submission_result.failure()
        logger.warning(f"Business logic error in run submission: {error_message}")
        return jsonify({"error": error_message}), 400

    run_responses = run_submission_result.unwrap()
    response = {"runResponses": run_responses}
    return jsonify(response), 200


@app.route("/runs", methods=["GET"])
@require_headers("Offline-Token", "Fredcli-Version")
def get_runs():
    """
    Get runs by job ID.
    Implements the get runs interaction from the Pact contract.
    """
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400

    try:
        job_id = int(job_id)
    except ValueError:
        return jsonify({"error": "Invalid job_id parameter"}), 400

    job_controller = get_job_controller()
    runs_result = job_controller.get_runs(job_id=job_id)

    if not is_successful(runs_result):
        error_message = runs_result.failure()
        logger.warning(f"Business logic error in get runs: {error_message}")
        return jsonify({"error": error_message}), 400

    response = {"runs": runs_result.unwrap()}

    return jsonify(response), 200


@app.route("/jobs/results", methods=["GET"])
@require_headers("Offline-Token", "Fredcli-Version")
def get_job_results():
    """
    Get URLs for runs by job ID.
    Returns a JSON response with URLs for all runs associated with the job.
    """
    job_id = request.args.get("job_id")
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400

    try:
        job_id = int(job_id)
    except ValueError:
        return jsonify({"error": "Invalid job_id parameter"}), 400

    job_controller = get_job_controller()
    runs_result = job_controller.get_runs(job_id=job_id)

    if not is_successful(runs_result):
        error_message = runs_result.failure()
        logger.warning(f"Business logic error in get job results: {error_message}")
        return jsonify({"error": error_message}), 400

    runs = runs_result.unwrap()

    # Extract URLs from runs
    urls = [
        {"run_id": run.get("id"), "url": run.get("config_url")}
        for run in runs
        if run.get("config_url") is not None
    ]

    return jsonify({"urls": urls}), 200


@app.route("/health", methods=["GET"])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route("/", methods=["GET"])
def root():
    """Root endpoint with API information."""
    return (
        jsonify(
            {
                "name": "Epistemix API",
                "version": "1.0.0",
                "description": "Interface for creating and running jobs on Epistemix platform",
                "endpoints": {
                    "POST /jobs/register": "Register a new job",
                    "POST /jobs": "Submit a job for processing",
                    "POST /runs": "Submit run requests",
                    "GET /runs": "Get runs by job_id",
                    "GET /jobs/results": "Get URLs for runs by job_id",
                    "GET /health": "Health check",
                },
            }
        ),
        200,
    )


if __name__ == "__main__":
    # Load environment variables
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    app.run(host=host, port=port, debug=debug)

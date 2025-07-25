"""
Flask app that implements the Epistemix API based on the Pact contract.
This app follows Clean Architecture principles with proper separation of concerns.
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
from datetime import datetime
from typing import Dict, List, Any
import logging
from functools import wraps
from returns.pipeline import is_successful
from pydantic import ValidationError

# Import our business models and controllers
from epistemix_api.controllers.job_controller import JobController
from epistemix_api.repositories.job_repository import SQLAlchemyJobRepository
from epistemix_api.repositories.database import get_database_manager
from epistemix_api.models.requests import RegisterJobRequest, SubmitJobRequest

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure database
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///epistemix_jobs.db')


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
    if hasattr(e, 'code') and e.code is not None:
        return e
    
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.before_request
def before_request():
    """Initialize database session for each request."""
    database_url = app.config['DATABASE_URL']
    db_manager = get_database_manager(database_url)
    g.db_session = db_manager.get_session()


@app.teardown_appcontext
def close_db_session(error):
    """Close database session after each request."""
    db_session = getattr(g, 'db_session', None)
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


def get_job_controller():
    """Get a JobController instance with the current request's database session."""
    session_factory = lambda: g.db_session
    job_repository = SQLAlchemyJobRepository(session_factory)
    return JobController.create_with_job_repository(job_repository)

# Legacy in-memory storage for runs (to be refactored later)
runs_storage: Dict[int, Dict[str, Any]] = {}
next_run_id = 978


def validate_headers(required_headers: List[str]) -> bool:
    """Validate that required headers are present in the request."""
    for header in required_headers:
        if header not in request.headers:
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


def require_json(content_type='application/json'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Validate content type
            if request.headers.get('content-type') != content_type:
                return jsonify({"error": f"Content-Type must be {content_type}"}), 400
            
            # Get and validate JSON data
            raw_data = request.get_json()
            if not raw_data:
                return jsonify({"error": "Invalid JSON"}), 400
            
            # Pass the JSON data as the first argument to the route function
            return f(raw_data, *args, **kwargs)
        return decorated_function
    return decorator


@app.route('/jobs/register', methods=['POST'])
@require_headers('Offline-Token', 'content-type', 'fredcli-version', 'user-agent')
@require_json('application/json')
def register_job(json_data):
    """Persists a new job to Epistemix platform."""
    request_data = RegisterJobRequest(**json_data)
    
    job_controller = get_job_controller()
    job_result = job_controller.register_job(
        user_id=request_data.userId, 
        tags=request_data.tags
    )
    
    if not is_successful(job_result):
        error_message = job_result.failure()
        logger.warning(f"Business logic error in job registration: {error_message}")
        return jsonify({"error": error_message}), 400

    return jsonify(job_result.unwrap()), 200        


@app.route('/jobs', methods=['POST'])
@require_headers('Offline-Token', 'content-type', 'fredcli-version', 'user-agent')
@require_json('application/json')
def submit_job(json_data):
    """Submit registered job for processing to Epistemix platform."""
    request_data = SubmitJobRequest(**json_data)
    
    job_controller = get_job_controller()
    job_submission_result = job_controller.submit_job(
        job_id=request_data.jobId, 
        context=request_data.context, 
        job_type=request_data.type
    )
    
    if not is_successful(job_submission_result):
        error_message = job_submission_result.failure()
        logger.warning(f"Business logic error in job submission: {error_message}")
        return jsonify({"error": error_message}), 400
    
    return jsonify(job_submission_result.unwrap()), 200


@app.route('/runs', methods=['POST'])
@require_headers('Offline-Token', 'Fredcli-Version')
def submit_runs():
    """
    Submit run requests.
    Implements the run submission interaction from the Pact contract.
    """
    global next_run_id
    
    data = request.get_json()
    if not data or 'runRequests' not in data:
        return jsonify({"error": "Invalid JSON or missing runRequests"}), 400
    
    run_requests = data['runRequests']
    run_responses = []
    
    for run_request in run_requests:
        job_id = run_request.get('jobId')
        if not job_id:
            return jsonify({"error": "Missing jobId in run request"}), 400
        
        # Create run response
        run_id = next_run_id
        run_response = {
            "runId": run_id,
            "jobId": job_id,
            "status": "Submitted",
            "errors": None,
            "runRequest": run_request
        }
        
        # Store run for later retrieval
        run_record = {
            "id": run_id,
            "jobId": job_id,
            "userId": 555,  # Mock user ID
            "createdTs": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "request": run_request,
            "podPhase": "Running",
            "containerStatus": None,
            "status": "DONE",
            "userDeleted": False,
            "epxClientVersion": request.headers.get('User-Agent', 'epx_client_1.2.2').split('_')[-1] if '_' in request.headers.get('User-Agent', '') else "1.2.2"
        }
        
        runs_storage[run_id] = run_record
        run_responses.append(run_response)
        next_run_id += 1
    
    response = {
        "runResponses": run_responses
    }
    
    return jsonify(response), 200


@app.route('/runs', methods=['GET'])
@require_headers('Offline-Token', 'Fredcli-Version')
def get_runs():
    """
    Get runs by job ID.
    Implements the get runs interaction from the Pact contract.
    """
    job_id = request.args.get('job_id')
    if not job_id:
        return jsonify({"error": "Missing job_id parameter"}), 400
    
    try:
        job_id = int(job_id)
    except ValueError:
        return jsonify({"error": "Invalid job_id parameter"}), 400
    
    # Filter runs by job ID
    matching_runs = [run for run in runs_storage.values() if run['jobId'] == job_id]
    
    response = {
        "runs": matching_runs
    }
    
    return jsonify(response), 200


@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Epistemix API",
        "version": "1.0.0",
        "description": "Interface for creating and running jobs on Epistemix platform",
        "endpoints": {
            "POST /jobs/register": "Register a new job",
            "POST /jobs": "Submit a job for processing", 
            "POST /runs": "Submit run requests",
            "GET /runs": "Get runs by job_id",
            "GET /jobs/statistics": "Get job statistics",
            "GET /health": "Health check"
        }
    }), 200


if __name__ == '__main__':
    # Load environment variables
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)

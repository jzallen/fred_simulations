"""
Flask app that implements the Epistemix API based on the Pact contract.
This app follows Clean Architecture principles with proper separation of concerns.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import logging

# Import our business models and services
from .models.job import Job, JobStatus, JobTag
from .services.job_service import JobService, JobRepository

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services (Dependency Injection in a real app)
job_service = JobService(JobRepository())

# Legacy in-memory storage for runs (to be refactored later)
runs_storage: Dict[int, Dict[str, Any]] = {}
next_run_id = 978


def validate_headers(required_headers: List[str]) -> bool:
    """Validate that required headers are present in the request."""
    for header in required_headers:
        if header not in request.headers:
            return False
    return True


@app.route('/jobs/register', methods=['POST'])
def register_job():
    """
    Register a new job.
    Implements the job registration interaction from the Pact contract.
    Uses Clean Architecture with business models and services.
    """
    # Validate required headers
    required_headers = ['Offline-Token', 'content-type', 'fredcli-version', 'user-agent']
    if not validate_headers(required_headers):
        return jsonify({"error": "Missing required headers"}), 400
    
    # Validate content type
    if request.headers.get('content-type') != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Extract business data
        tags = data.get("tags", [])
        user_id = 456  # Mock user ID as per Pact contract
        
        # Use business service to register the job
        job = job_service.register_job(user_id=user_id, tags=tags)
        
        # Return response matching Pact contract
        return jsonify(job.to_dict()), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in job registration: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in job registration: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/jobs', methods=['POST'])
def submit_job():
    """
    Submit a job for processing.
    Implements the job submission interaction from the Pact contract.
    Uses Clean Architecture with business services.
    """
    # Validate required headers
    required_headers = ['Offline-Token', 'content-type', 'fredcli-version', 'user-agent']
    if not validate_headers(required_headers):
        return jsonify({"error": "Missing required headers"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        # Extract business data
        job_id = data.get("jobId")
        context = data.get("context", "job")
        job_type = data.get("type", "input")
        
        if not job_id:
            return jsonify({"error": "Missing jobId"}), 400
        
        # Use business service to submit the job
        response = job_service.submit_job(job_id=job_id, context=context, job_type=job_type)
        
        return jsonify(response), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in job submission: {e}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in job submission: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/runs', methods=['POST'])
def submit_runs():
    """
    Submit run requests.
    Implements the run submission interaction from the Pact contract.
    """
    global next_run_id
    
    # Validate required headers (more flexible validation for the run submission)
    required_headers = ['Offline-Token', 'Fredcli-Version']
    if not validate_headers(required_headers):
        return jsonify({"error": "Missing required headers"}), 400
    
    try:
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
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/runs', methods=['GET'])
def get_runs():
    """
    Get runs by job ID.
    Implements the get runs interaction from the Pact contract.
    """
    # Validate required headers
    required_headers = ['Offline-Token', 'Fredcli-Version']
    if not validate_headers(required_headers):
        return jsonify({"error": "Missing required headers"}), 400
    
    try:
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
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200


@app.route('/jobs/statistics', methods=['GET'])
def get_job_statistics():
    """
    Get job statistics endpoint.
    Demonstrates Clean Architecture by using business services.
    """
    try:
        stats = job_service.get_job_statistics()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error getting job statistics: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Epistemix API Mock",
        "version": "1.0.0",
        "description": "Mock implementation of Epistemix API based on Pact contract with Clean Architecture",
        "architecture": "Clean Architecture with Domain Models and Services",
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

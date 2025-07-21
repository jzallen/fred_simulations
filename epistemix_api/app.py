"""
Flask app that implements the Epistemix API based on the Pact contract.
This app mocks the behavior defined in epx-epistemix.json.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
from typing import Dict, List, Any

app = Flask(__name__)
CORS(app)

# In-memory storage for demo purposes
jobs_storage: Dict[int, Dict[str, Any]] = {}
runs_storage: Dict[int, Dict[str, Any]] = {}
next_job_id = 123
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
    """
    global next_job_id
    
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
        
        # Create job record
        job_id = next_job_id
        user_id = 456  # Mock user ID as per Pact contract
        
        job = {
            "id": job_id,
            "userId": user_id,
            "tags": data.get("tags", [])
        }
        
        jobs_storage[job_id] = job
        next_job_id += 1
        
        return jsonify(job), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/jobs', methods=['POST'])
def submit_job():
    """
    Submit a job for processing.
    Implements the job submission interaction from the Pact contract.
    """
    # Validate required headers
    required_headers = ['Offline-Token', 'content-type', 'fredcli-version', 'user-agent']
    if not validate_headers(required_headers):
        return jsonify({"error": "Missing required headers"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400
        
        job_id = data.get("jobId")
        if not job_id or job_id not in jobs_storage:
            return jsonify({"error": "Invalid job ID"}), 400
        
        # Return pre-signed URL as per Pact contract
        response = {
            "url": "http://localhost:5001/pre-signed-url"
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "Epistemix API Mock",
        "version": "1.0.0",
        "description": "Mock implementation of Epistemix API based on Pact contract",
        "endpoints": {
            "POST /jobs/register": "Register a new job",
            "POST /jobs": "Submit a job for processing", 
            "POST /runs": "Submit run requests",
            "GET /runs": "Get runs by job_id",
            "GET /health": "Health check"
        }
    }), 200


if __name__ == '__main__':
    # Load environment variables
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)

# Epistemix API Mock Server

This Flask application implements a mock server for the Epistemix API based on the Pact contract defined in `pacts/epx-epistemix.json`.

## Features

- **Full Pact Contract Compliance**: Implements all endpoints and responses defined in the Pact contract
- **Job Management**: Register and submit jobs
- **Run Management**: Submit and retrieve simulation runs
- **CORS Support**: Configured for cross-origin requests
- **Health Checks**: Built-in health monitoring
- **Comprehensive Testing**: Full test suite validating Pact compliance

## API Endpoints

### POST /jobs/register
Register a new job with the system.

**Request Headers:**
- `Offline-Token`: Bearer token for authentication
- `content-type`: application/json
- `fredcli-version`: Version of the FRED CLI
- `user-agent`: Client user agent

**Request Body:**
```json
{
  "tags": ["info_job"]
}
```

**Response:**
```json
{
  "id": 123,
  "userId": 456,
  "tags": ["info_job"]
}
```

### POST /jobs
Submit a job for processing.

**Request Headers:**
- `Offline-Token`: Bearer token for authentication
- `content-type`: application/json
- `fredcli-version`: Version of the FRED CLI
- `user-agent`: Client user agent

**Request Body:**
```json
{
  "jobId": 123,
  "context": "job",
  "type": "input"
}
```

**Response:**
```json
{
  "url": "http://localhost:5001/pre-signed-url"
}
```

### POST /runs
Submit run requests for simulation execution.

**Request Headers:**
- `Offline-Token`: Bearer token for authentication
- `Fredcli-Version`: Version of the FRED CLI
- Other headers as needed

**Request Body:**
```json
{
  "runRequests": [
    {
      "jobId": 123,
      "workingDir": "/workspaces/fred_simulations",
      "size": "hot",
      "fredVersion": "latest",
      "population": {
        "version": "US_2010.v5",
        "locations": ["Loving_County_TX"]
      },
      "fredArgs": [
        {
          "flag": "-p",
          "value": "main.fred"
        }
      ],
      "fredFiles": [
        "/workspaces/fred_simulations/simulations/agent_info_demo/agent_info.fred"
      ]
    }
  ]
}
```

**Response:**
```json
{
  "runResponses": [
    {
      "runId": 978,
      "jobId": 123,
      "status": "Submitted",
      "errors": null,
      "runRequest": { /* original request */ }
    }
  ]
}
```

### GET /runs
Retrieve runs by job ID.

**Query Parameters:**
- `job_id`: ID of the job to get runs for

**Request Headers:**
- `Offline-Token`: Bearer token for authentication
- `Fredcli-Version`: Version of the FRED CLI

**Response:**
```json
{
  "runs": [
    {
      "id": 978,
      "jobId": 123,
      "userId": 555,
      "createdTs": "2023-10-01T12:00:00Z",
      "request": { /* original run request */ },
      "podPhase": "Running",
      "containerStatus": null,
      "status": "DONE",
      "userDeleted": false,
      "epxClientVersion": "1.2.2"
    }
  ]
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-10-01T12:00:00.000000"
}
```

### GET /
Root endpoint with API information.

## Running the Server

### Using the run script:
```bash
cd /workspaces/fred_simulations/epistemix_platform
python run_server.py
```

### Using Flask directly:
```bash
cd /workspaces/fred_simulations/epistemix_platform
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### Using Poetry (from project root):
```bash
cd /workspaces/fred_simulations
poetry run python epistemix_platform/run_server.py
```

## Environment Variables

- `FLASK_HOST`: Host to bind to (default: 0.0.0.0)
- `FLASK_PORT`: Port to listen on (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: True)
- `FLASK_ENV`: Environment mode (development, testing, production)
- `CORS_ORIGINS`: Allowed CORS origins (default: *)

## Testing

Run the test suite to validate Pact contract compliance:

```bash
cd /workspaces/fred_simulations
poetry run pytest epistemix_platform/tests/ -v
```

## Development

The Flask app is structured as follows:

- `app.py`: Main Flask application with all endpoints
- `config.py`: Configuration classes for different environments
- `run_server.py`: Script to run the server
- `tests/test_pact_compliance.py`: Comprehensive test suite
- `requirements.txt`: Python dependencies
- `pacts/epx-epistemix.json`: Pact contract definition

## Architecture

This mock server maintains in-memory storage for jobs and runs. In a production environment, you would replace this with a proper database backend. The server implements the exact request/response patterns defined in the Pact contract to ensure compatibility with clients expecting the real Epistemix API.

## Notes

- All endpoints validate required headers as specified in the Pact contract
- Job and run IDs are auto-incremented starting from the values in the Pact contract
- The server returns mock data that matches the structure expected by clients
- CORS is enabled to support browser-based clients

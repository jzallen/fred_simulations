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
- `DATABASE_URL`: PostgreSQL connection string (defaults to SQLite if not set)
- `DATABASE_POOL_SIZE`: Connection pool size for PostgreSQL (default: 10)
- `DATABASE_MAX_OVERFLOW`: Maximum overflow connections (default: 20)
- `DATABASE_POOL_TIMEOUT`: Connection pool timeout in seconds (default: 30)

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

## Database and Migrations

The platform supports both SQLite (default) and PostgreSQL databases with Alembic for schema migrations.

### PostgreSQL Setup

#### Starting PostgreSQL
```bash
# Start PostgreSQL container
docker-compose up -d postgres

# Check logs
docker-compose logs -f postgres

# Stop database
docker-compose down
```

#### Building Migration Runner
The migration runner is a Docker image that contains Alembic and can be used for both local development and as a bastion for production RDS migrations.

```bash
# Build the migration runner image
pants package //:migration-runner
```

#### Running Migrations
```bash
# Check current migration status
docker-compose run --rm migration-runner alembic current

# Run all pending migrations
docker-compose run --rm migration-runner alembic upgrade head

# Create a new migration
docker-compose run --rm migration-runner alembic revision --autogenerate -m "Description"

# Rollback last migration
docker-compose run --rm migration-runner alembic downgrade -1

# Reset database (drop and recreate)
docker-compose down -v
docker-compose up -d postgres
docker-compose run --rm migration-runner alembic upgrade head
```

#### Running SQL Queries
```bash
# Single query
docker-compose run --rm migration-runner psql "postgresql://epistemix_user:epistemix_password@postgres:5432/epistemix_db" -c "SELECT * FROM jobs;"

# Interactive session
docker-compose run --rm migration-runner psql "postgresql://epistemix_user:epistemix_password@postgres:5432/epistemix_db"

# Direct access to postgres container
docker exec -it epistemix_postgres psql -U epistemix_user -d epistemix_db
```

#### Production RDS Migrations
The migration runner can act as a bastion for running migrations against production RDS:

```bash
# Set your production RDS connection string
export DATABASE_URL="postgresql://prod_user:password@your-rds-endpoint.amazonaws.com:5432/prod_db"

# Run migrations
docker-compose run --rm -e DATABASE_URL migration-runner alembic upgrade head

# Check status
docker-compose run --rm -e DATABASE_URL migration-runner alembic current
```

### Migration Structure
```
epistemix_platform/
├── alembic.ini                 # Alembic configuration
├── migrations/
│   ├── env.py                  # Alembic environment config
│   ├── script.py.mako          # Migration template
│   └── versions/               # Migration files
│       └── 001_initial_migration.py
└── src/epistemix_platform/
    └── repositories/
        └── database.py         # SQLAlchemy models & manager
```

### Database Configuration
- **Local Development**: Uses dockerized PostgreSQL or SQLite fallback
- **Production**: Connects to AWS RDS via DATABASE_URL
- **Backward Compatibility**: Falls back to SQLite when DATABASE_URL is not set
- **Connection Pooling**: Configurable pool settings for PostgreSQL

## Notes

- All endpoints validate required headers as specified in the Pact contract
- Job and run IDs are auto-incremented starting from the values in the Pact contract
- The server returns mock data that matches the structure expected by clients
- CORS is enabled to support browser-based clients
- Database migrations are managed via Alembic with support for both SQLite and PostgreSQL
- The migration runner Docker image is built using Pants and can be used as a production bastion

# FRED Simulation Runner

A dedicated component for orchestrating FRED epidemiological simulations with support for downloading configurations, FRED 10/11+ compatibility, and simulation execution.

## Overview

The Simulation Runner provides a complete workflow for running FRED simulations from EPX job configurations:

1. **Download** job uploads from S3 via Epistemix API
2. **Extract** archives (job_input.zip)
3. **Prepare** FRED 10 configuration files from EPX run configs
4. **Validate** configurations using FRED -c flag
5. **Execute** FRED simulations
6. **Collect** outputs and logs

## Architecture

This component follows clean architecture patterns consistent with the fred_simulations project:

```
simulation_runner/
├── src/simulation_runner/       # Source code
│   ├── cli.py                  # Click CLI interface
│   ├── config.py               # Configuration management
│   ├── workflow.py             # Simulation orchestration
│   ├── fred_config_builder.py  # FRED 10 config builder
│   ├── exceptions.py           # Custom exceptions
│   └── utils/                  # Utility functions
│       └── date_converter.py   # Date format conversion
├── tests/                      # Unit tests
│   ├── test_fred_config_builder.py
│   ├── test_date_converter.py
│   └── integration/            # Integration tests
├── scripts/                    # Shell scripts (backward compat)
│   └── run-simulation.sh      # Bash wrapper
├── BUILD                       # Pants build configuration
├── pyproject.toml             # Python dependencies
└── README.md                  # This file
```

## Installation

### Using Pants (Recommended for Production)

```bash
# Build the PEX binary
pants package simulation_runner:simulation-runner-cli

# The binary will be at: dist/simulation_runner/simulation-runner-cli.pex

# Run it
./dist/simulation_runner/simulation-runner-cli.pex --help
```

### Using Poetry (Local Development)

```bash
cd simulation_runner
poetry install
poetry run simulation-runner --help
```

## Usage

### CLI Commands

#### Run Complete Workflow

Run the full simulation pipeline from download to execution:

```bash
# Process all runs for a job
simulation-runner run --job-id 12

# Process specific run
simulation-runner run --job-id 12 --run-id 4
```

#### Validate Only

Validate FRED configurations without running simulations:

```bash
simulation-runner validate --job-id 12
simulation-runner validate --job-id 12 --run-id 4
```

#### Prepare Config

Convert EPX run config to FRED 10 format:

```bash
simulation-runner prepare run_4_config.json main.fred prepared.fred
simulation-runner prepare run_config.json main.fred out.fred --verbose
```

#### Download Only

Download job uploads without processing:

```bash
simulation-runner download --job-id 12
simulation-runner download --job-id 12 --output-dir /tmp/job_12
```

#### Show Configuration

Display current environment configuration:

```bash
simulation-runner config
```

#### Version Info

Show simulation runner version:

```bash
simulation-runner version
```

## Configuration Management

The simulation runner uses a flexible configuration system that supports multiple sources:

### Configuration Priority (Highest to Lowest)

1. **Environment Variables** - Direct environment variable overrides
2. **Local .env File** - For local development (not committed to git)
3. **AWS Parameter Store** - For staging/production deployments
4. **Built-in Defaults** - Fallback values

### Local Development with .env Files

For local development, copy the example configuration:

```bash
cd simulation_runner
cp .env.example .env
# Edit .env with your local values
```

The `.env` file is automatically loaded when the CLI starts. Example `.env`:

```bash
# Local development configuration
FRED_HOME=/workspaces/fred_simulations/fred-framework
WORKSPACE_DIR=/workspace

# Database
DATABASE_URL=postgresql://epistemix_user:epistemix_password@localhost:5432/epistemix_db

# API and S3
EPISTEMIX_API_URL=http://localhost:5000
EPISTEMIX_S3_BUCKET=epistemix-uploads-dev
AWS_REGION=us-east-1

# Environment
ENVIRONMENT=dev
```

### Production with AWS Parameter Store

In staging/production environments, configuration is loaded from AWS Systems Manager Parameter Store:

```bash
# Parameters are stored at:
# /{application_name}/{environment}/{parameter_name}
#
# Example parameters:
# /epistemix_platform/production/DB_HOST
# /epistemix_platform/production/DB_PASSWORD
# /epistemix_platform/production/EPISTEMIX_API_URL
# /epistemix_platform/production/EPISTEMIX_S3_BUCKET

# Set ENVIRONMENT to enable Parameter Store loading
export ENVIRONMENT=production
export APPLICATION_NAME=epistemix_platform

# Run simulation runner (will load from Parameter Store)
simulation-runner run --job-id 12
```

**Note:** FRED_HOME and WORKSPACE_DIR are NOT stored in Parameter Store as they are environment-specific paths.

### Configuration Variables

| Variable | Description | Default | In Parameter Store? |
|----------|-------------|---------|---------------------|
| `FRED_HOME` | Path to FRED framework installation | **Required** | No (local only) |
| `WORKSPACE_DIR` | Workspace for downloads/outputs | `/workspace/job_{id}` | No (local only) |
| `DATABASE_URL` | Database connection string | `sqlite:///epistemix_jobs.db` | Yes (or individual DB params) |
| `DB_HOST` | Database host | - | Yes |
| `DB_PORT` | Database port | `5432` | Yes |
| `DB_NAME` | Database name | - | Yes |
| `DB_USER` | Database user | - | Yes |
| `DB_PASSWORD` | Database password | - | Yes (SecureString) |
| `EPISTEMIX_API_URL` | Epistemix API endpoint | - | Yes |
| `EPISTEMIX_S3_BUCKET` | S3 bucket for uploads | - | Yes |
| `AWS_REGION` | AWS region | `us-east-1` | Yes |
| `ENVIRONMENT` | Environment name (dev/staging/production) | `dev` | No |
| `APPLICATION_NAME` | Application name for Parameter Store | `epistemix_platform` | No |

### Running with Different Configurations

```bash
# Local development with .env file
cd simulation_runner
cp .env.example .env
# Edit .env
simulation-runner run --job-id 12

# Override specific variables
FRED_HOME=/custom/path simulation-runner run --job-id 12

# Production with Parameter Store
export ENVIRONMENT=production
export FRED_HOME=/fred-framework
simulation-runner run --job-id 12

# Check current configuration
simulation-runner config
```

### Docker Usage

The simulation-runner is packaged in a Docker image:

```bash
# Build the Docker image
pants package //:simulation-runner

# Run with environment variables
docker run \
  -e FRED_HOME=/fred-framework \
  -e EPISTEMIX_API_URL=http://host.docker.internal:5000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  simulation-runner:latest run --job-id 12

# Mount local directory to access outputs
docker run \
  -v $(pwd)/outputs:/workspace \
  -e FRED_HOME=/fred-framework \
  -e DATABASE_URL=postgresql://... \
  simulation-runner:latest run --job-id 12
```

## Development

### Running Tests

```bash
# Using Pants
pants test simulation_runner::

# Using Poetry
cd simulation_runner
poetry run pytest

# With coverage
poetry run pytest --cov=simulation_runner --cov-report=html
```

### Code Quality

```bash
# Format code
poetry run black src/ tests/
poetry run isort src/ tests/

# Lint
poetry run flake8 src/ tests/
poetry run pylint src/simulation_runner
```

## API Reference

### FREDConfigBuilder

Builder pattern for creating FRED 10 configuration files:

```python
from pathlib import Path
from simulation_runner.fred_config_builder import FREDConfigBuilder

# From run config JSON
builder = FREDConfigBuilder.from_run_config(
    Path("run_4_config.json"),
    Path("main.fred")
)
prepared_fred = builder.build(Path("prepared.fred"))

# Fluent API
builder = (
    FREDConfigBuilder(Path("main.fred"))
    .with_dates("2020-01-01", "2020-03-31")
    .with_locations(["Allegheny_County_PA"])
    .with_seed(12345)
    .build(Path("out.fred"))
)
```

### SimulationWorkflow

Orchestrates the complete simulation pipeline:

```python
from simulation_runner.config import SimulationConfig
from simulation_runner.workflow import SimulationWorkflow

# Create configuration
config = SimulationConfig.from_env(job_id=12, run_id=4)

# Run workflow
workflow = SimulationWorkflow(config)
workspace = workflow.execute()

# Or run individual stages
workflow.download_uploads()
workflow.extract_archives()
prepared_runs = workflow.prepare_configs()
validated_runs = workflow.validate_configs(prepared_runs)
completed_runs = workflow.run_simulations(validated_runs)
```

### SimulationConfig

Configuration management:

```python
from simulation_runner.config import SimulationConfig

# From environment
config = SimulationConfig.from_env(job_id=12, run_id=4)

# Validate
errors = config.validate()
if errors:
    print(f"Configuration errors: {errors}")

# Get FRED binary path
fred_binary = config.get_fred_binary()
```

## Compatibility Notes

### FRED 10 vs FRED 11+

This component bridges the gap between EPX (designed for FRED 11+) and FRED 10:

- **FRED 10** (v5.7.0, University of Pittsburgh): Parameters in .fred file
  ```fred
  start_date = 2020-Jan-01
  locations = Allegheny_County_PA
  ```

- **FRED 11+** (Epistemix commercial): Parameters as CLI flags
  ```bash
  FRED --start-date 2020-01-01 -l Allegheny_County_PA
  ```

The `FREDConfigBuilder` automatically converts EPX configs (FRED 11+ format) to FRED 10 .fred files.

## Troubleshooting

### FRED_HOME not found

```
ConfigurationError: FRED_HOME environment variable is required
```

**Solution:** Set FRED_HOME to your FRED installation:
```bash
export FRED_HOME=/workspaces/fred_simulations/fred-framework
```

### Download fails

```
DownloadError: Failed to download uploads for job 12
```

**Solution:** Check database connectivity and AWS credentials:
```bash
# Test database connection
simulation-runner config

# Verify AWS credentials
aws sts get-caller-identity
```

### Validation fails

```
ValidationError: FRED validation failed for run 4
```

**Solution:** Check the validation log for details:
```bash
cat /workspace/job_12/run_4_validation.log
```

## Contributing

When adding new features:

1. Follow clean architecture patterns
2. Add unit tests (>80% coverage)
3. Update documentation
4. Run code quality checks
5. Test with Pants build system

## License

Part of the fred_simulations project.

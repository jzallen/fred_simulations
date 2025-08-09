# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FRED (Framework for Reconstructing Epidemiological Dynamics) simulation project with three main components:
1. **fred-framework/**: Core FRED simulation engine (C++ source)
2. **epistemix_api/**: Flask-based mock API server for Epistemix API
3. **simulations/**: Agent-based simulation configurations and scripts

## Common Development Commands

### Building and Running FRED Simulations
```bash
# Build FRED framework (if needed)
make build-fred
# or
cd fred-framework/src && make

# Run FRED simulation via CLI
make run-fred
# or
./run_fred_simulation.sh

# Analyze simulation results
make analyze
# or
python3 analyze_results.py

# Complete workflow (run + analyze)
make run-and-analyze

# Clean generated files
make clean
```

### Python Development (using Poetry)
```bash
# Install dependencies
poetry install --no-root

# Run tests for epistemix_api (in parallel)
make test
# or
poetry run pytest epistemix_api/ -n auto

# Run specific test file
poetry run pytest epistemix_api/tests/test_pact_compliance.py -v

# Code Quality Commands
make format       # Format code with black and isort
make lint         # Run all linters (black, flake8, pylint)
make lint-fix     # Auto-fix formatting and show remaining issues
make pre-commit   # Run pre-commit hooks on all files

# Or use Poetry directly:
poetry run black epistemix_api/ simulations/ *.py
poetry run flake8 epistemix_api/ simulations/ *.py
poetry run pylint epistemix_api/ simulations/ *.py
```

### Epistemix API Server
```bash
# Run the mock API server
cd epistemix_api
python run_server.py

# Or using Poetry from project root
poetry run python epistemix_api/run_server.py
```

## High-Level Architecture

### FRED Framework Structure
The FRED framework (`fred-framework/`) is a compiled C++ epidemiological simulation engine:
- **src/**: Core simulation engine with classes for Person, Place, Epidemic, Transmission models
- **bin/**: Compiled executables including `FRED`, `fred_run`, `fred_plot`, `fred_stats`
- **data/**: Location data for US counties, states, demographics
- **models/**: Pre-built simulation models (influenza, vaccine scenarios, school closure)

### Epistemix API Mock Server
The `epistemix_api/` directory implements a Flask-based mock server following Pact contract specifications:
- **Clean Architecture Pattern**: Separates controllers, use cases, repositories, and models
- **Repository Pattern**: Database abstraction through interfaces (SQLAlchemy and in-memory implementations)
- **Pact Contract Testing**: All endpoints validated against `pacts/epx-epistemix.json`
- **Key endpoints**: `/jobs/register`, `/jobs`, `/runs` for job submission and monitoring

### Simulation Workflow
1. Configuration files (`.fred` format) define simulation parameters
2. FRED executable processes the configuration with location data
3. Results are output to `output/` directory as CSV files
4. Python scripts analyze and visualize the results

## Key Configuration Files
- **simulation_config.fred**: Generated FRED simulation configuration
- **pyproject.toml**: Poetry dependencies and project metadata
- **epistemix_api/pacts/**: Pact contracts defining API specifications

## Testing Strategy
- **Unit tests**: Located in `epistemix_api/tests/` using pytest with parallel execution (`-n auto`)
- **Pact compliance**: `test_pact_compliance.py` validates API contract
- **Integration tests**: Test database repositories and API endpoints
- **Code Quality Enforcement**:
  - **Pre-commit hooks**: Automatically run black, isort, flake8, and pylint on commit
  - **Pre-push hooks**: Run all epistemix_api tests in parallel before push
  - **Linting**: PEP8 compliance via black (formatting) and flake8 (style checks)
  - **Static analysis**: pylint configured with project-specific rules in `.pylintrc`

## Important Notes
- FRED_HOME environment variable should point to `/workspaces/fred_simulations/fred-framework`
- The project uses Poetry for Python dependency management - always use `poetry run` or activate the virtual environment
- API server runs on port 5000 by default with CORS enabled
- Simulation output goes to `output/` directory with run-specific subdirectories


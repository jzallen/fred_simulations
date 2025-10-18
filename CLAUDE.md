# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FRED (Framework for Reconstructing Epidemiological Dynamics) simulation project using **Pants build system** for Python dependency management and PEX binary creation. The repository contains:

1. **fred-framework/**: Core FRED simulation engine (C++ source)
2. **epistemix_platform/**: Flask-based mock API server implementing Epistemix API with clean architecture
   - Also includes AWS infrastructure templates (CloudFormation/Sceptre) in `infrastructure/` subdirectory
3. **simulation_runner/**: FRED simulation orchestration component (Python CLI with clean architecture)
4. **simulations/**: Agent-based simulation configurations and scripts
5. **tcr/**: Test && Commit || Revert (TCR) development tool

## Common Development Commands

### Pants Build System Commands
```bash
# Generate/update lockfiles for Python dependencies
pants generate-lockfiles
pants generate-lockfiles --resolve=epistemix_platform_env

# Export dependencies to virtual environment
pants export --resolve=epistemix_platform_env

# Build PEX binaries
pants package epistemix_platform:epistemix-cli
pants package simulation_runner:simulation-runner-cli
pants package tcr:tcr-cli
pants package epistemix_platform:epistemix_platform_test_runner

# Run tests with Pants
pants test ::  # Run all tests
pants test epistemix_platform::  # Run epistemix_platform tests
pants test simulation_runner::  # Run simulation_runner tests
pants test tcr::  # Run TCR tests
```

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

### Python Development (using Poetry for local development)
```bash
# Install dependencies
poetry install --no-root

# Run tests for epistemix_platform (in parallel)
make test
# or
poetry run pytest epistemix_platform/ -n auto

# Run specific test file
poetry run pytest epistemix_platform/tests/test_pact_compliance.py -v

# Code Quality Commands
make format       # Format code with black and isort
make lint         # Run all linters (black, flake8, pylint)
make lint-fix     # Auto-fix formatting and show remaining issues
make pre-commit   # Run pre-commit hooks on all files

# Or use Poetry directly:
poetry run black epistemix_platform/ simulations/ *.py
poetry run flake8 epistemix_platform/ simulations/ *.py
poetry run pylint epistemix_platform/ simulations/ *.py
```

### Epistemix API Server
```bash
# Run the mock API server
cd epistemix_platform
python run_server.py

# Or using Poetry from project root
poetry run python epistemix_platform/run_server.py
```

### Simulation Runner (NEW Python CLI)
```bash
# Build simulation-runner CLI
pants package simulation_runner:simulation-runner-cli

# Run complete simulation workflow
./dist/simulation_runner/simulation-runner-cli.pex run --job-id 12
./dist/simulation_runner/simulation-runner-cli.pex run --job-id 12 --run-id 4

# Validate configs without running simulations
./dist/simulation_runner/simulation-runner-cli.pex validate --job-id 12

# Download job uploads only
./dist/simulation_runner/simulation-runner-cli.pex download --job-id 12

# Prepare FRED config from run config
./dist/simulation_runner/simulation-runner-cli.pex prepare run_4_config.json main.fred prepared.fred

# Show configuration
./dist/simulation_runner/simulation-runner-cli.pex config

# Show version
./dist/simulation_runner/simulation-runner-cli.pex version
```

### Docker Images
```bash
# Build Docker images using Pants
pants package //:simulation-runner  # FRED simulation runner
pants package //:epistemix-api       # API server
pants package //:migration-runner    # Database migrations

# Run simulation-runner container (Python CLI - default)
docker run \
  -e FRED_HOME=/fred-framework \
  -e EPISTEMIX_API_URL=http://host.docker.internal:5000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  simulation-runner:latest run --job-id 12

# Show simulation-runner help
docker run simulation-runner:latest --help

# Validate configs only
docker run \
  -e FRED_HOME=/fred-framework \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  simulation-runner:latest validate --job-id 12

# Use epistemix-cli directly in the container
docker run --rm --entrypoint epistemix-cli \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  simulation-runner:latest jobs list
```

## High-Level Architecture

### Build System - Pants
This project uses **Pants** as the primary build system for Python components:
- **Dependency Management**: Three separate Python resolves (dependency groups):
  - `epistemix_platform_env`: Main platform dependencies
  - `infrastructure_env`: AWS infrastructure/Sceptre dependencies
  - `tcr_env`: TCR tool dependencies
- **PEX Binaries**: Creates standalone Python executables for:
  - `epistemix-cli`: Command-line interface for Epistemix API
  - `tcr-cli`: Test && Commit || Revert development tool
  - `epistemix_platform_test_runner`: VS Code test discovery support
- **Source Roots**: Configured for `epistemix_platform/src`, `tcr/src`, and project root

### Component Details
Each major component has its own README.md with detailed documentation:
- **fred-framework/**: C++ epidemiological simulation engine
- **epistemix_platform/**: Flask API server with clean architecture and AWS infrastructure templates
- **simulation_runner/**: FRED simulation orchestration with Python CLI, clean architecture, and workflow management
- **simulations/**: FRED simulation configurations and analysis scripts
- **tcr/**: Development workflow tool for rapid feedback cycles

## Key Configuration Files
- **pants.toml**: Pants build system configuration with Python resolves and source roots
- **pyproject.toml**: Poetry dependencies for local development
- **BUILD files**: Pants build targets throughout the repository
- **simulation_config.fred**: Generated FRED simulation configuration
- **epistemix_platform/pacts/**: Pact contracts defining API specifications

## Git Commit Convention

This project follows the **Conventional Commits** standard (https://www.conventionalcommits.org/). All commits should use the following format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Commit Types:
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc.)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **build**: Changes that affect the build system or external dependencies
- **ci**: Changes to CI configuration files and scripts
- **chore**: Other changes that don't modify src or test files
- **revert**: Reverts a previous commit

### Examples:
- `feat(api): Add endpoint for batch job submission`
- `fix: Resolve race condition in simulation runner`
- `docs: Update README with new installation steps`
- `refactor(epistemix_platform): Extract repository interface`
- `test: Add integration tests for job scheduler`
- `chore: Update dependencies in pyproject.toml`

## Testing Strategy
- **Unit tests**: Located in `epistemix_platform/tests/` using pytest with parallel execution (`-n auto`)
- **Pact compliance**: `test_pact_compliance.py` validates API contract
- **Integration tests**: Test database repositories and API endpoints
- **Code Quality Enforcement**:
  - **Pre-commit hooks**: Automatically run black, isort, flake8, and pylint on commit
  - **Pre-push hooks**: Run all epistemix_platform tests in parallel before push
  - **Linting**: PEP8 compliance via black (formatting) and flake8 (style checks)
  - **Static analysis**: pylint configured with project-specific rules in `.pylintrc`

## Important Notes
- FRED_HOME environment variable should point to `/workspaces/fred_simulations/fred-framework`
- The project uses **Pants** for building PEX binaries and managing Python dependencies across multiple resolves
- Poetry is used for local development and quick iterations; Pants is used for production builds
- API server runs on port 5000 by default with CORS enabled
- Simulation output goes to `output/` directory with run-specific subdirectories
- Pants lockfiles are stored in component-specific locations (e.g., `epistemix_platform/epistemix_platform_env.lock`)

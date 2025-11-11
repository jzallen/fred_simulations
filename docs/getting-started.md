# Getting Started

## Dependencies

This project uses **Pants build system** for Python dependency management. Poetry is used for basic dev environment setup, but all project dependencies are managed with Pants through component-specific lockfiles for reproducible builds.

### Pants Build System

Pants is used to manage Python dependencies, create PEX binaries, and run tests. Key concepts:

#### Generating Lockfiles

Generate or update lockfiles for Python dependencies:

```bash
# Generate lockfiles for all resolves (Python dependency groups)
pants generate-lockfiles

# Generate lockfile for a specific resolve
pants generate-lockfiles --resolve=epistemix_platform_env

# Common resolves in this project:
# - epistemix_platform_env: Dependencies for the Epistemix API platform
# - infrastructure_env: Dependencies for AWS infrastructure deployment (Sceptre, cfn-lint)
# - simulation_runner_env: Dependencies for the simulation runner CLI
# - simulations_env: Dependencies for simulation job scripts
# - tcr_env: Dependencies for the TCR development tool
```

Lockfiles are stored in component-specific locations (e.g., `epistemix_platform/epistemix_platform_env.lock`, `simulation_runner/simulation_runner_env.lock`).

#### Creating Virtual Environments from Lockfiles

Export Python dependencies from lockfiles to create virtual environments:

```bash
# Export all dependencies for a specific resolve
pants export --resolve=epistemix_platform_env

# The virtual environment will be created in the gitignored dist/ directory:
# dist/export/python/virtualenvs/epistemix_platform_env/<python-version>/

# To use this environment in VS Code:
# 1. Open Command Palette (Ctrl+Shift+P)
# 2. Type "Python: Select Interpreter"
# 3. Choose "Enter interpreter path..."
# 4. Navigate to: dist/export/python/virtualenvs/epistemix_platform_env/<version>/bin/python
```

#### Building PEX Binaries

Create standalone Python executables:

```bash
# Build the Epistemix CLI (job & results management)
pants package epistemix_platform:epistemix-cli

# Build the Simulation Runner CLI (FRED workflow orchestration)
pants package simulation_runner:simulation-runner-cli

# Build the test runner
pants package epistemix_platform:epistemix_platform_test_runner

# Build TCR (Test && Commit || Revert) tool
pants package tcr:tcr-cli

# Build Docker images
pants package //:simulation-runner  # FRED simulation runner
pants package //:epistemix-api       # API server
pants package //:migration-runner    # Database migrations
```

#### Running Tests

Run tests using Pants:

```bash
# Run all tests in epistemix_platform
pants test epistemix_platform::

# Run specific test file
pants test epistemix_platform/tests/test_app_routes.py

# Run tests with coverage
pants test --test-use-coverage epistemix_platform::

# Run tests in parallel (default)
pants test epistemix_platform:: --pytest-args="-n auto"
```

### Poetry (Local Development)

Poetry is used for basic dev environment setup. All project dependencies are managed with Pants.

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dev dependencies for IDE support and local testing
poetry install --no-root
```

## Quick Start

Run FRED simulation using the CLI interface:

```bash
make run-fred
# or directly:
./run_fred_simulation.sh
```

Analyze simulation results with Python:

```bash
make analyze
# or directly:
python3 analyze_results.py
```

Run simulation and analyze in one command:

```bash
make run-and-analyze
```

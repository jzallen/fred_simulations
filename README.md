# FRED Simulation Project

This project demonstrates how to work with the FRED (Framework for Reconstructing Epidemiological Dynamics) simulation framework using its CLI interface.

## Dependencies

This project uses Pants build system with Poetry for Python dependency management. Dependencies are managed through lockfiles for reproducible builds.

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
# - root: Root-level Python dependencies
```

The lockfiles are stored in `3rdparty/python/` directory (which is gitignored).

#### Creating Virtual Environments from Lockfiles

Export Python dependencies from lockfiles to create virtual environments:

```bash
# Export all dependencies for a specific resolve
pants export --resolve=epistemix_platform_env

# The virtual environment will be created in:
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
# Build the Epistemix CLI
pants package epistemix_platform:epistemix-cli

# Build the test runner
pants package epistemix_platform:epistemix_platform_test_runner

# Build TCR (Test && Commit || Revert) tool
pants package tcr:tcr-cli
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

### Poetry (Legacy)

Poetry is still used in some components. If you need to install Poetry dependencies directly:

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --no-root
```

## Project Structure

- `run_fred_simulation.sh` - **Main simulation script**: Uses FRED's CLI interface
- `fred_cli_demo.sh` - Demonstration of available FRED CLI commands
- `fred-framework/` - FRED framework submodule with all source code and binaries
- `simulation_config.fred` - Generated configuration file for FRED simulations

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

## FRED CLI Commands

The FRED framework provides many CLI utilities:

- `FRED` - Main simulation executable
- `fred_run` - Run simulations
- `fred_plot` - Create visualizations
- `fred_stats` - Generate statistics
- `fred_csv` - Convert output to CSV

See `./fred_cli_demo.sh` for a complete overview.

## Configuration

FRED simulations are configured using `.fred` files. Example:

```
# Basic configuration
locations = Allegheny_County_PA
days = 10
verbose = 1
enable_health_records = 1

# Disease model
condition Influenza {
    transmissibility = 0.5
    symptomatic_fraction = 0.67
    incubation_days = uniform(1, 3)
    infectious_days = uniform(3, 7)
    recovery_days = uniform(5, 10)
}
```

## Output

Simulation results are stored in the `output/` directory:
- `output/RUN1/out.csv` - Daily population and epidemic statistics
- `output/RUN1/Influenza.csv` - Disease-specific metrics
- `output/RUN1/health_records.txt` - Individual health records
- `output/warnings.txt` - Warnings log

## Available Locations

The framework includes sample data for these locations:
- `Allegheny_County_PA` - Allegheny County, PA (Pittsburgh area, ~1.2M people)
- `Jefferson_County_PA` - Jefferson County, PA (rural area)

## Make Targets

Available make targets:
- `make run-fred` - Run FRED simulation via CLI
- `make analyze` - Analyze simulation results with Python/pandas
- `make run-and-analyze` - Run simulation and analyze results
- `make build-fred` - Build the FRED framework
- `make clean` - Remove generated output files
- `make help` - Show available targets

## VS Code Tasks

Configured tasks:
- **Build FRED Framework** - Compiles the FRED framework
- **Run FRED Simulation (CLI)** - Runs the simulation
- **Analyze FRED Results** - Runs Python analysis on results
- **Run FRED and Analyze** - Complete workflow from simulation to analysis
- **Clean FRED Output** - Removes generated files

## Data Analysis

The project includes a Python script (`analyze_results.py`) that uses pandas and matplotlib to:
- Load and analyze FRED simulation output
- Create visualizations of population and disease dynamics
- Generate summary statistics
- Save plots as PNG files

Required Python packages (automatically installed in devcontainer):
- pandas
- matplotlib
- seaborn
- numpy
- jupyter
- plotly

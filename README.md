# FRED Simulation Project

This project demonstrates how to work with the FRED (Framework for Reconstructing Epidemiological Dynamics) simulation framework using its CLI interface.

## Dependencies

This project uses Poetry for Python dependency management. The dependencies are locked in `poetry.lock` for reproducible builds.

### Installing Dependencies

Poetry is automatically installed in the devcontainer. If you're running locally:

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
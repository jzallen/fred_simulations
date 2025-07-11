# FRED Simulation Project

This project demonstrates how to work with the FRED (Framework for Reconstructing Epidemiological Dynamics) simulation framework using its CLI interface.

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
locations = 42003
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
- `output/RUN1/health_records.txt` - Health records
- `output/errors.txt` - Error log

## Available Locations

The framework includes sample data for these locations:
- `42003` - Allegheny County, PA
- `42065` - Jefferson County, PA

## Make Targets

Available make targets:
- `make run-fred` - Run FRED simulation via CLI
- `make build-fred` - Build the FRED framework
- `make clean` - Remove generated output files
- `make help` - Show available targets

## VS Code Tasks

Configured tasks:
- **Build FRED Framework** - Compiles the FRED framework
- **Run FRED Simulation (CLI)** - Runs the simulation
- **Clean FRED Output** - Removes generated files
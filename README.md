# FRED Simulation Project

This project demonstrates how to work with the FRED (Framework for Reconstructing Epidemiological Dynamics) simulation framework, both through direct C++ integration and via the CLI interface.

## Project Structure

- `main.cpp` - C++ program that demonstrates direct integration with FRED libraries (for reference)
- `run_fred_simulation.sh` - **Primary approach**: Bash script that uses FRED's CLI interface
- `fred_cli_demo.sh` - Demonstration of available FRED CLI commands
- `fred-framework/` - FRED framework submodule with all source code and binaries
- `simulation_config.fred` - Generated configuration file for FRED simulations

## Quick Start

### Method 1: CLI Approach (Recommended)

Run FRED simulation using the CLI interface:

```bash
make run-fred
# or directly:
./run_fred_simulation.sh
```

### Method 2: C++ Integration (For Reference)

Build and run the C++ integration example:

```bash
make simulation
./simulation
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

## Why CLI vs C++?

FRED is designed primarily as a CLI tool. While C++ integration is possible, the CLI approach is:
- ✅ Simpler to use and maintain
- ✅ More stable and well-documented
- ✅ Better supported by the FRED team
- ✅ Easier to configure and customize

The C++ integration is kept for educational purposes and advanced use cases.

## Available Locations

The framework includes sample data for these locations:
- `42003` - Allegheny County, PA
- `42065` - Jefferson County, PA

## Tasks

VS Code tasks are configured:
- **Build FRED Simulation** - Compiles the C++ version
- **Run FRED Simulation (C++)** - Runs the C++ version
- **Run FRED Simulation (CLI)** - Runs the bash script version
# CLI Tools

## Simulation Runner CLI

The `simulation-runner-cli` orchestrates complete FRED simulation workflows:

```bash
# Build the CLI
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

See [simulation_runner/README.md](../simulation_runner/README.md) for detailed documentation.

## Epistemix Platform CLI

The `epistemix-cli` manages jobs and results:

```bash
# Build the CLI
pants package epistemix_platform:epistemix-cli

# Upload simulation results to S3
./dist/epistemix_platform/epistemix-cli.pex jobs results upload \
  --job-id 12 \
  --run-id 4 \
  --results-dir ./output/RUN4

# List jobs
./dist/epistemix_platform/epistemix-cli.pex jobs list

# Get job info
./dist/epistemix_platform/epistemix-cli.pex jobs info --job-id 12

# Download job uploads
./dist/epistemix_platform/epistemix-cli.pex jobs uploads download \
  --job-id 12 \
  --output-dir ./downloads \
  --force

# Archive job uploads (move to Glacier storage)
./dist/epistemix_platform/epistemix-cli.pex jobs uploads archive \
  --job-id 12 \
  --days-since-create 30 \
  --dry-run
```

See [epistemix_platform/README.md](../epistemix_platform/README.md) for detailed documentation.

# FRED Simulation Project

A platform for running epidemiological simulations in the cloud built on the FRED (Framework for Reconstructing Epidemiological Dynamics) framework and epx client for FRED jobs.

## Overview

This project combines:

- **FRED Framework**: C++ epidemiological simulation engine
- **Epistemix Platform**: Flask-based API server with clean architecture and AWS infrastructure
- **Simulation Runner**: Python CLI for orchestrating FRED simulation workflows
- **Simulations**: Agent-based simulation configurations and job scripts
- **TCR**: Test && Commit || Revert development tool

Built with **Pants** for dependency management, PEX binaries, and Docker images.

## Project Components

- **[fred-framework/](fred-framework/)** - C++ epidemiological simulation engine
- **[epistemix_platform/](epistemix_platform/)** - Flask API server with clean architecture
  - **[infrastructure/](epistemix_platform/infrastructure/)** - AWS CloudFormation/Sceptre templates
- **[simulation_runner/](simulation_runner/)** - FRED workflow orchestration with Python CLI
- **[simulations/](simulations/)** - Simulation configurations and job scripts
- **[tcr/](tcr/)** - Test && Commit || Revert development tool

## Documentation

- **[Getting Started](docs/getting-started.md)** - Installation, dependencies, and quick start
- **[Architecture](docs/architecture.md)** - Project structure and technology stack
- **[FRED Simulations](docs/fred-simulations.md)** - Running and configuring FRED simulations
- **[CLI Tools](docs/cli-tools.md)** - Simulation Runner and Epistemix Platform CLIs
- **[Docker Containers](docs/docker.md)** - Building and running Docker images
- **[AWS Infrastructure](docs/aws-infrastructure.md)** - Deploying to AWS with CloudFormation/Sceptre

## Technology Stack

- **Build System**: Pants (Python dependency management, PEX binaries, Docker images)
- **Backend**: Python 3.11, Flask, SQLAlchemy, Alembic
- **Database**: PostgreSQL with RDS IAM authentication
- **Infrastructure**: AWS (Lambda, RDS, S3, API Gateway, ECR)
- **Infrastructure as Code**: CloudFormation, Sceptre
- **Testing**: pytest, Pact (contract testing)
- **Code Quality**: Ruff (linting + formatting)
- **Containers**: Docker (multi-stage builds with Pants)

## Common Commands

### Build System

```bash
# Generate lockfiles
pants generate-lockfiles

# Export virtual environment
pants export --resolve=epistemix_platform_env

# Build PEX binaries
pants package epistemix_platform:epistemix-cli
pants package simulation_runner:simulation-runner-cli

# Build Docker images
pants package //:simulation-runner
pants package //:epistemix-api

# Run tests
pants test ::
```

## License

See individual component READMEs for license information.

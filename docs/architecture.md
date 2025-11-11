# Architecture

## Project Structure

- `run_fred_simulation.sh` - **Main simulation script**: Uses FRED's CLI interface
- `fred_cli_demo.sh` - Demonstration of available FRED CLI commands
- `fred-framework/` - FRED framework submodule with all source code and binaries
- `epistemix_platform/` - Flask-based API server implementing Epistemix API with clean architecture
  - `infrastructure/` - AWS infrastructure templates (CloudFormation/Sceptre) for deploying to AWS
- `simulation_runner/` - Python CLI for orchestrating FRED simulation workflows
- `simulations/` - Agent-based simulation configurations and job scripts
- `tcr/` - Test && Commit || Revert (TCR) development tool
- `simulation_config.fred` - Generated configuration file for FRED simulations

## Component Architecture

Each major component has its own README with detailed documentation:

- **[fred-framework/](../fred-framework/)** - C++ epidemiological simulation engine
- **[epistemix_platform/](../epistemix_platform/)** - Flask API server with clean architecture
  - **[infrastructure/](../epistemix_platform/infrastructure/)** - AWS CloudFormation/Sceptre templates
- **[simulation_runner/](../simulation_runner/)** - FRED workflow orchestration with Python CLI
- **[simulations/](../simulations/)** - Simulation configurations and job scripts
- **[tcr/](../tcr/)** - Test && Commit || Revert development tool

### Technology Stack

- **Build System**: Pants (Python dependency management, PEX binaries, Docker images)
- **Backend**: Python 3.11, Flask, SQLAlchemy, Alembic
- **Database**: PostgreSQL with RDS IAM authentication
- **Infrastructure**: AWS (Lambda, RDS, S3, API Gateway, ECR)
- **Infrastructure as Code**: CloudFormation, Sceptre
- **Testing**: pytest, Pact (contract testing)
- **Code Quality**: Ruff (linting + formatting)
- **Containers**: Docker (multi-stage builds with Pants)

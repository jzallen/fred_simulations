# Changelog

All notable changes to simulation_runner will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-10-18

### Added
- **FRED-27**: Complete simulation-runner Python CLI with clean architecture
  - Click-based command-line interface with six commands: `run`, `validate`, `prepare`, `download`, `config`, `version`
  - Workflow orchestration for FRED simulation pipeline (download → extract → prepare → validate → execute)
  - FRED 10/11+ configuration builder with date/location/seed parameter injection
  - S3 upload download integration via epistemix-cli
  - Docker image with epistemix-cli and FRED binary
  - Comprehensive test suite with pytest (24 unit tests)
  - Date conversion utilities for ISO ↔ FRED 10 format
  - Exception hierarchy for error handling (ConfigurationError, WorkflowError, ValidationError, etc.)
  - Environment-based configuration management (DATABASE_URL, AWS credentials, S3 bucket)
  - Influenza demo simulation with job execution script

### Changed
- Build system integration with Pants
  - Added `simulation_runner_env` Python resolve
  - PEX binary generation for standalone CLI distribution
  - Dependency management via pyproject.toml (PEP 621 + Poetry)
  - UTF-8 encoding for all file I/O operations

### Fixed
- Python version constraint alignment between PEP 621 and Poetry (`>=3.11,<3.12`)
- Replaced `sys.exit()` with `click.ClickException` for consistent error handling
- Removed unused imports and extraneous f-string prefixes
- Improved error logging with `logger.exception()` for stack traces
- Removed shebang from non-executable Python module

### Technical Details
- Clean architecture with separation of concerns (config, workflow, builders, exceptions)
- Dependency injection for testability
- Repository pattern for data access
- Type hints throughout codebase
- Comprehensive docstrings following NumPy style
- PEP 8 compliance via black, flake8, pylint

[Unreleased]: https://github.com/jzallen/fred_simulations/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/jzallen/fred_simulations/releases/tag/v1.0.0

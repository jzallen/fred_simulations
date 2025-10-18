# Changelog

All notable changes to FRED Simulations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **FRED-28**: Migrated from pre-commit framework to Pants-native linting using Ruff
  - Added Ruff backends to Pants (`pants.backend.experimental.python.lint.ruff.check` and `pants.backend.experimental.python.lint.ruff.format`)
  - Created root `pyproject.toml` with Ruff configuration (Black-compatible settings)
  - Created Git hooks (`.git/hooks/pre-commit` and `.git/hooks/pre-push`) for automated linting
  - Removed `.pre-commit-config.yaml` (legacy pre-commit framework configuration)
  - Updated `CLAUDE.md` documentation with Pants linting commands
  - **Performance improvement**: 10-100x faster linting and formatting vs pre-commit framework
  - **Simplified toolchain**: Single tool (Ruff) replaces 4 tools (black, isort, flake8, pylint)
  - **Better caching**: Pants manages caching across all linting operations

[Unreleased]: https://github.com/jzallen/fred_simulations/compare/HEAD...HEAD

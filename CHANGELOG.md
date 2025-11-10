# Changelog

All notable changes to the FRED Simulations project will be documented in this file.

This changelog focuses on project-level changes: build system, development workflow, tooling, and documentation. For component-specific changes, see:
- `epistemix_platform/CHANGELOG.md` - API server and infrastructure
- `simulation_runner/CHANGELOG.md` - FRED simulation orchestration
- `tcr/CHANGELOG.md` - Test && Commit || Revert tool
- `epistemix_platform/infrastructure/CHANGELOG.md` - AWS CloudFormation templates

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## 2025-11-10

### Removed
- Obsolete scripts and tests from project root
  - `fred_cli_demo.sh` - Replaced by epistemix-cli and simulation-runner-cli
  - `run_epistemix_api.sh` - Replaced by Docker infrastructure
  - `run_fred_simulation.sh` - Replaced by simulation-runner-cli
  - `run_info_job.py` - Replaced by epistemix-cli jobs commands
  - `run_info_job_debug.py` - Debugging script no longer needed
  - `test_cli_setup.py` - Early CLI testing replaced by proper test suite
  - `test_poetry_setup.py` - Dependency setup testing no longer needed

## 2025-11-07

### Added
- **Skills**: New Claude Code skills for development patterns
  - `pants-build-system` - Expert guidance on Pants build system usage
  - `gateway-builder` - Clean architecture external service integration
  - Updated `tdd` skill for optimal Pants caching

### Changed
- **Skills**: Reorganized skills with progressive disclosure pattern
  - Optimized for token efficiency with reference directories
  - Improved skill organization and discoverability
- **software-architect**: Enhanced multi-engineer workflow
  - Worktree support for parallel ENGINEER-nn explorations
  - Improved BDD and TDD integration
  - Better context management

## 2025-11-06

### Fixed
- Gitpod: Install Claude CLI globally with npm -g flag
  - Ensures Claude CLI available in PATH for all sessions

## 2025-11-03

### Added
- **Skills**: SKILL.md file naming convention
  - Renamed all Skill.md files to SKILL.md in `.claude/skills/`
  - Consistent capitalization across skills directory

### Changed
- **software-architect**: Updated with multi-engineer workflow patterns
  - Enhanced build-one-to-throw-away methodology
  - Improved engineer personas and synthesis

## 2025-10-24

### Added
- **Skills**: Reorganized subagents into skills-based architecture
  - Migrated from `.claude/agents/` to `.claude/skills/`
  - Better organization and reusability

## 2025-10-22

### Added
- AWS knowledge MCP server integration
  - Enhanced AWS documentation and resource lookups
  - Removed unused agent configurations

## 2025-10-18

### Changed
- **Build System**: Migrated from pre-commit framework to Pants-native linting using Ruff (#58)
  - Added Ruff backends to Pants (`pants.backend.experimental.python.lint.ruff.check` and `pants.backend.experimental.python.lint.ruff.format`)
  - Created root `pyproject.toml` with Ruff configuration (Black-compatible settings)
  - Created Git hooks (`.git/hooks/pre-commit` and `.git/hooks/pre-push`) for automated linting
  - Removed `.pre-commit-config.yaml` (legacy pre-commit framework configuration)
  - Updated `CLAUDE.md` documentation with Pants linting commands
  - **Performance improvement**: 10-100x faster linting and formatting vs pre-commit framework
  - **Simplified toolchain**: Single tool (Ruff) replaces 4 tools (black, isort, flake8, pylint)
  - **Better caching**: Pants manages caching across all linting operations

## 2025-09-29

### Changed
- **Documentation**: Updated `CLAUDE.md` to reflect Pants build system usage
  - Comprehensive build commands and workflow documentation
  - Component-specific build targets
  - Docker image build instructions

### Fixed
- Gitpod automation tasks set to manual-only
  - Avoids dependency installation issues on workspace startup
  - Users can manually trigger tasks when needed

## 2025-09-26

### Added
- **Build System**: PEX test runner and improved VS Code integration
  - `epistemix_platform_test_runner` PEX binary for VS Code test discovery
  - Better IDE integration for test execution
  - Enhanced development workflow

## 2025-09-24

### Fixed
- **Development**: Removed VS Code settings from repository (#48)
  - `.vscode/settings.json` now local-only via `.gitignore`
  - Prevents conflicts between developer preferences
- **AWS CLI**: Migrated to AWS CLI v2 and documented jsonschema constraints (#51)
  - Updated documentation for CLI v2 breaking changes
  - Improved AWS service integration

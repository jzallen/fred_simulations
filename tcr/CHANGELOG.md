# Changelog

All notable changes to TCR (Test && Commit || Revert) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-09-22

### Changed
- Restructured module to use src directory layout for better organization
- Implemented dependency injection for loggers throughout the codebase

## [0.0.3] - 2025-09-17

### Added
- Session-based logging with `--session-id` CLI option for tracking multiple TCR instances
- `ls` command to list all running TCR sessions
- `stop` command with required session-id to stop specific TCR sessions
- Process naming as `tcr:session_id` for better visibility in process managers
- Session-based watch_paths scoping

### Fixed
- Handle pgrep's 15 character pattern limit in stop command
- Test build configuration to include conftest.py

## [0.0.2] - 2025-09-15

### Changed
- Simplified TCR implementation and updated documentation

### Fixed
- Boolean type conversion issue in CloudFormation ECR template

## [0.0.1] - 2025-09-13

### Added
- Initial implementation of TCR pattern for AI-constrained development
- Test && Commit || Revert workflow enforcement
- Automatic file watching and test execution
- Configuration support via tcr.yaml
- CLI interface with `start` command
- Pants build system integration for standalone executable
- Comprehensive test suite including unit and integration tests
- Documentation and example configuration files
- Support for custom test commands and ignore patterns
- Git integration for automatic commits and reverts

[Unreleased]: https://github.com/jzallen/fred_simulations/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jzallen/fred_simulations/compare/v0.0.3...v0.1.0
[0.0.3]: https://github.com/jzallen/fred_simulations/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/jzallen/fred_simulations/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/jzallen/fred_simulations/releases/tag/v0.0.1
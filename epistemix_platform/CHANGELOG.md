# Changelog

All notable changes to epistemix_platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-09-23

### Changed
- Moved pact files to simulations directory for better organization

## [0.0.4] - 2025-09-22

### Changed
- Renamed from epistemix_api to epistemix_platform
- Restructured to src directory layout

## [0.0.3] - 2025-09-15

### Added
- ECR and S3 infrastructure with Sceptre migration
- Docker support for FRED simulation runner

### Fixed
- Boolean type conversion in CloudFormation ECR template

## [0.0.2] - 2025-09-02

### Changed
- Implemented clean architecture patterns
- Refactored to eliminate circular dependencies via dependency injection

### Added
- S3 lifecycle management for cost efficiency
- Job uploads list with sanitized URLs
- Download functionality for archives

### Fixed
- ZIP archive download error
- Preserve order in upload location deduplication
- Extended S3 lifecycle policy to prevent data loss

## [0.0.1] - 2025-08-06

### Added
- Mock server implementation for Epistemix API
- Full Pact contract compliance
- Job registration and submission endpoints
- Run management endpoints
- CORS support for cross-origin requests
- Health check endpoints
- CLI interface for server operations
- Token generation utility
- Comprehensive test suite with Pact validation
- Repository pattern with SQLAlchemy
- Clean architecture with controllers, models, and mappers
- S3 upload bucket CloudFormation template

[Unreleased]: https://github.com/jzallen/fred_simulations/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jzallen/fred_simulations/compare/v0.0.4...v0.1.0
[0.0.4]: https://github.com/jzallen/fred_simulations/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/jzallen/fred_simulations/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/jzallen/fred_simulations/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/jzallen/fred_simulations/releases/tag/v0.0.1
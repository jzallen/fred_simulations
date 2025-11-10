# Changelog

All notable changes to epistemix_platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2025-11-09

### Added
- **FRED-47**: Batch presigned URL generation for job results endpoint (#73)
  - New RunResults domain model with run_id and url fields
  - get_run_results use case for batch URL generation with 24-hour expiration
  - Reconstructs S3 paths using JobS3Prefix.from_job() for consistency
  - Single batch operation reduces API overhead
  - Comprehensive test suite for batch operations

### Changed
- Refactored GET /jobs/results endpoint for batch operations
  - JobController.get_run_results_download signature updated
  - Changed from (run_id, results_url) to (job_id, bucket_name)
  - Eliminated dependency on persisted results_url fields
  - Endpoint remains backward compatible with API contract

### Removed
- agent_info_demo replaced by working influenza simulation demo

## [0.8.0] - 2025-11-08

### Added
- **FRED-46**: AWS Batch status synchronization for run polling (#72)
  - BatchStatusMapper for AWS Batch status to domain enum mapping
  - RunStatusDetail model now includes pod_phase field
  - update_run_status use case for status synchronization
  - Retry logic with exponential backoff for transient AWS errors
  - Graceful degradation returns stale DB status when Batch unavailable
  - Status transition and metrics logging for observability
  - PodPhase to RunStatus mapping for epx alignment
- **FRED-45**: AWS Batch integration for FRED simulation runner
  - Batch job submission and monitoring capabilities
  - Integration with simulation_runner for cloud-based execution

### Changed
- Run.natural_key converted from method to @property
  - More Pythonic API for computed attributes
  - Updated all call sites to use property access

### Fixed
- AWS Batch IAM permissions for status synchronization
  - Separated BatchAccessPolicy into resource-specific and wildcard statements
  - batch:ListJobs and batch:DescribeJobs require Resource: "*" (AWS API constraint)
  - Lambda can now query Batch job status during polling
- Test assertions to match status synchronization behavior
  - Tests now account for get_runs() querying AWS Batch
  - Expected status updated from QUEUED to RUNNING in integration tests

## [0.7.0] - 2025-11-06

### Changed
- **FRED-36**: Standardized Sceptre stack management
  - Migrated secrets to AWS Secrets Manager
  - Improved infrastructure as code practices

## [0.6.0] - 2025-11-04

### Added
- **FRED-44**: IAM authentication for RDS database connections (#71)
  - Secure passwordless authentication using AWS IAM tokens
  - Token auto-refresh for long-running processes
  - SSL/TLS enforcement for database connections

### Security
- IAM database authentication eliminates password storage
- Enhanced security posture with token-based access

## [0.5.0] - 2025-11-03

### Added
- **FRED-43**: migration-runner Docker integration with bootstrap module (#70)
  - Shared AWS configuration loading in entrypoint
  - Consistent environment handling across services
- **FRED-41**: Bootstrap module integration in Flask app and CLI (#68)
  - Centralized AWS configuration management
  - python-dotenv integration for local development
- **FRED-40**: Bootstrap module for shared AWS configuration (#67)
  - Reusable AWS config loader with environment variable support
  - Standardized configuration across all services
- **FRED-39**: Parameter Store CloudFormation templates and IAM policies (#66)
  - Secure secrets management infrastructure
  - Least-privilege IAM policies for parameter access

## [0.4.1] - 2025-10-30

### Changed
- **FRED-38**: Refactored job controller for readability and cohesion (#65)
  - Extracted complex methods into focused use cases
  - Improved separation of concerns
  - Enhanced testability

## [0.4.0] - 2025-10-28

### Changed
- **FRED-34**: simulation-runner now uses epistemix-cli for results upload (#62)
  - Shared results upload logic across services
  - Reduced code duplication

## [0.3.2] - 2025-10-25

### Added
- **FRED-35**: JobS3Prefix model for consistent timestamp-based S3 paths (#61)
  - Refactored S3UploadLocationRepository to use JobS3Prefix
  - Consistent S3 key structure across all operations

## [0.3.1] - 2025-10-24

### Added
- **FRED-31**: epistemix-cli results upload with clean architecture and JobS3Prefix (#60)
  - Clean architecture implementation with use cases and gateways
  - Automatic S3 key generation using JobS3Prefix
  - Integration with S3UploadLocationRepository

## [0.3.0] - 2025-10-22

### Added
- **FRED-31**: epistemix-cli command to upload simulation results to S3 (#59)
  - `jobs results upload` command for uploading simulation results to S3
  - S3 integration for results storage

## [0.2.2] - 2025-10-18

### Added
- **FRED-27**: Complete simulation-runner with Python CLI and clean architecture (#57)
  - Simulation runner integration capabilities
  - Enhanced workflow orchestration

### Changed
- **FRED-28**: Replaced pre-commit framework with Pants-native Ruff linting (#58)
  - 10-100x faster linting and formatting
  - Integrated into Pants build system
  - Black-compatible formatting rules

### Fixed
- S3 presigned URL generation for staging compliance
  - Removed ServerSideEncryption parameter from presigned URLs
  - Fixed compatibility with S3 buckets requiring server-side encryption
  - Added clarifying comments in s3_upload_location_repository.py
  - Updated test suite to validate presigned URL parameters

## [0.2.1] - 2025-10-15

### Added
- **FRED-30**: Secured RDS database deployment (#56)
  - Database deployed in private subnets only (PubliclyAccessible: false)
  - SSM bastion for secure administrative access
  - Port forwarding support for local tools

### Security
- Database no longer publicly accessible

## [0.2.0] - 2025-10-13

### Added
- **FRED-29**: AWS API Gateway + Lambda architecture (#55)
  - Replaced nginx with serverless API Gateway
  - Lambda function with VPC configuration for RDS access
  - Improved scalability and reduced operational overhead

## [0.1.4] - 2025-10-06

### Added
- **FRED-26**: PostgreSQL migration from SQLite (#54)
  - AWS RDS PostgreSQL database integration
  - Enhanced data durability and query capabilities
  - Multi-user support with proper isolation

## [0.1.3] - 2025-09-29

### Added
- **FRED-25**: Docker containerization using Pants (#53)
  - epistemix-api Docker image with production-ready configuration
  - migration-runner image for database schema management
  - Pants-based build system for reproducible images

### Changed
- Updated resolve path for pants lock file generation for Python dependencies

## [0.1.2] - 2025-09-26

### Added
- PEX test runner and improved VS Code integration
  - Better development workflow
  - Enhanced testing capabilities

## [0.1.1] - 2025-09-24

### Fixed
- **FRED-19**: Migrated to AWS CLI v2 and documented jsonschema constraints (#51)
- **FRED-18**: Enhanced S3 CORS configuration with HEAD method (#52)
- **FRED-16**: Removed VS Code settings from repository (#48)
- **FRED-15**: Fixed test naming and documentation consistency (#49)
- **FRED-14**: Cleaned up Python linting and import issues (#50)
- **FRED-12**: Fixed Sceptre configuration issues (#44)
- **FRED-11**: Hardened subprocess execution in Sceptre hooks (#45)
- **FRED-10**: Fixed path traversal vulnerability in test runner (#46)

### Added
- **FRED-17**: CloudFormation deletion protection for production (#47)

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


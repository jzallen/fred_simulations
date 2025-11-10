# Changelog

All notable changes to the Epistemix Platform Infrastructure will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2025-11-09

### Changed
- **FRED-47**: Updated AWS Batch infrastructure tests
  - Updated test assertions for batch infrastructure template
  - Enhanced VPC endpoint testing for AWS Batch

## [0.6.0] - 2025-11-08

### Added
- **FRED-46**: AWS Batch IAM permissions for status synchronization (#72)
  - Separated BatchAccessPolicy into resource-specific and wildcard statements
  - Added batch:ListJobs and batch:DescribeJobs permissions (require Resource: "*")
  - Lambda can now query Batch job status during polling
- **FRED-45**: AWS Batch infrastructure for FRED simulation runner
  - Batch compute environment with EC2 and Fargate configurations
  - Job queue and job definition resources
  - VPC endpoints for AWS Batch service connectivity
  - IAM roles and policies for Batch job execution
  - Integration with ECS task execution

## [0.5.0] - 2025-11-06

### Changed
- **FRED-36**: Standardized Sceptre stack management
  - Migrated database credentials to AWS Secrets Manager
  - Removed Parameter Store usage for sensitive data
  - Improved infrastructure as code practices
  - Enhanced security posture with proper secrets management

## [0.4.0] - 2025-11-04

### Added
- **FRED-44**: IAM authentication for RDS database connections (#71)
  - Updated RDS CloudFormation template for IAM authentication support
  - Added IAMDatabaseAuthenticationEnabled parameter
  - Lambda IAM policy updates for RDS IAM authentication
  - SSL/TLS certificate configuration for secure connections

## [0.3.0] - 2025-11-03

### Added
- **FRED-43**: migration-runner infrastructure integration (#70)
  - Bootstrap module integration for AWS configuration
  - Consistent environment handling across services
- **FRED-41**: epistemix_platform infrastructure updates (#68)
  - Bootstrap module integration in infrastructure components
- **FRED-39**: Parameter Store CloudFormation templates and IAM policies (#66)
  - New CloudFormation template for Parameter Store resources
  - IAM policies for secure parameter access
  - Least-privilege access controls
  - Integration with existing infrastructure stacks

## [0.2.2] - 2025-10-30

### Changed
- **FRED-38**: Infrastructure test improvements (#65)
  - Updated tests for job controller refactoring
  - Enhanced test coverage

## [0.2.1] - 2025-10-29

### Added
- **FRED-32**: Sceptre hooks for CloudFormation template validation (#64)
  - Pre-create hooks for template syntax validation
  - cfn-lint integration for best practices checking
  - cfn-guard integration for security policy validation
  - Improved infrastructure deployment safety

### Changed
- **FRED-32**: Standardized infrastructure tests with CDK assertions (#63)
  - Migrated tests to use aws-cdk-lib assertions
  - Fixed integration test infrastructure setup
  - Improved test reliability and maintainability
  - Better error messages and debugging capabilities

## [0.2.0] - 2025-10-28

### Changed
- **FRED-34**: Updated infrastructure for epistemix-cli results upload (#62)
  - Lambda IAM policy updates for S3 results access
  - Enhanced S3 bucket policies for results operations

## [0.1.1] - 2025-10-18

### Added
- **FRED-27**: Staging environment infrastructure deployment
  - API Gateway REST API with /v1 stage deployment
  - Lambda function with VPC configuration for RDS access
  - ECR repository for epistemix-api Docker images
  - S3 upload bucket with CORS and lifecycle policies
  - SSM bastion for secure database access via port forwarding

### Changed
- **FRED-28**: Build system improvements (#58)
  - Replaced pre-commit framework with Pants-native workflows
  - Infrastructure tests integration with Pants
- Lambda security group integration for database connectivity
  - Added DBSecurityGroupId parameter to Lambda CloudFormation template
  - LambdaSecurityGroup resource with egress to RDS
  - RDS security group ingress rule from Lambda
  - VPC configuration (subnet IDs and security groups)
  - AWSLambdaVPCAccessExecutionRole added to execution role
- S3 bucket policy updates
  - Removed server-side encryption from presigned URL parameters
  - Retained HTTPS-only access enforcement
  - Fixed compatibility with staging S3 upload requirements

### Fixed
- SSM bastion security group references now use CloudFormation exports
  - Replaced hard-coded RDS security group IDs with stack exports
  - Improved cross-stack resource references

## [0.1.0] - 2025-10-15

### Added
- **FRED-30**: Secured RDS database by removing public accessibility
  - RDS instance now deployed in private subnets only (PubliclyAccessible: false)
  - Added DBSubnetGroup resource for multi-AZ private subnet deployment
  - Parameterized VPC configuration (VPCId, PrivateSubnetIds, VpcCidr)
  - Lambda security group integration for API database access
- SSM bastion infrastructure for secure administrative database access
  - EC2 t3.nano instance with SSM Session Manager agent
  - Port forwarding support for local database tools (psql, pgAdmin)
  - No SSH keys or public IPs required
- Staging environment infrastructure configuration

### Changed
- RDS security group now accepts connections from:
  - Lambda security group (for API operations)
  - SSM bastion security group (for admin access)
  - VPC CIDR block (configurable via VpcCidr parameter)
  - Optional developer IP (via DeveloperIP parameter)

### Security
- Database is no longer publicly accessible (critical security improvement)
- SSL/TLS encryption required for all database connections
- SSM Session Manager provides audited administrative access
- Removed public internet access (0.0.0.0/0) from security groups

## [2025-09-24]

### Changed
- **FRED-8**: Removed non-functional SNS notification feature from ECR template (#42)
  - Cleaned up unused SNS topic and subscription resources
  - Simplified ECR template by removing notification complexity

## [2025-09-23]

### Added
- **FRED-9**: Enforced S3 bucket encryption for security compliance (#41)
  - Added bucket policy to deny unencrypted uploads
  - Enforced HTTPS-only connections
  - Implemented AES256 server-side encryption by default
- Infrastructure tests target to Pants build system
  - Enabled automated testing of CloudFormation templates
  - Added validation checks for template syntax

### Changed
- Reorganized infrastructure BUILD files for better structure
  - Improved Pants build configuration
  - Better separation of test and production targets

## [2025-09-22]

### Changed
- Restructured epistemix_platform with src directory layout
  - Improved project organization
  - Better separation of concerns

## [2025-09-15]

### Fixed
- **FRED-7**: Fixed boolean type conversion in CloudFormation ECR template (#40)
  - Corrected EnableVulnerabilityScanning parameter handling
  - Fixed conditional logic for CloudWatch logs

## [2025-09-13]

### Added
- **FRED-22**: Implemented TCR pattern for AI-constrained development (#39)
  - Test && Commit || Revert pattern support
  - Improved development workflow

## [2025-09-12]

### Added
- **Initial Infrastructure Release**: Complete ECR and S3 infrastructure with Sceptre migration (#37)
  - ECR repository template with lifecycle policies
  - S3 upload bucket with CORS configuration
  - Sceptre configuration for dev/staging/production environments
  - IAM roles for EKS and EC2 access
  - CloudWatch logging and dashboards
  - Vulnerability scanning for container images
  - Lifecycle policies for cost optimization

## [2025-09-02]

### Changed
- Renamed epistemix_api to epistemix_platform (#36)
  - Better alignment with project scope
  - Consistent naming conventions

## Template Features

### ECR Repository Template
- **Security**: AES256 encryption, vulnerability scanning on push
- **Access Control**: IAM roles for EKS (IRSA) and EC2 instances
- **Lifecycle Management**: Automated image retention policies
- **Monitoring**: CloudWatch logs and dashboard for metrics
- **Cost Optimization**: Automatic cleanup of untagged and old images

### S3 Upload Bucket Template
- **Security**: Server-side encryption (AES256), HTTPS enforcement
- **Access Control**: IAM role for secure uploads
- **CORS**: Configurable origins for web uploads
- **Lifecycle**: Automatic archival to Glacier and expiration
- **Compliance**: Public access blocked, versioning enabled

## Security Improvements
- All resources enforce encryption at rest
- HTTPS-only access for S3 buckets
- Least privilege IAM policies
- Vulnerability scanning for container images
- Audit logging via CloudWatch

## Known Issues
- None at this time

## Upcoming Features
- CloudFormation drift detection automation
- Cost allocation tags refinement
- Cross-region replication for disaster recovery
- AWS Backup integration for S3 buckets
# Changelog

All notable changes to the Epistemix Platform Infrastructure will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **FRED-27**: Staging environment infrastructure deployment
  - API Gateway REST API with /v1 stage deployment
  - Lambda function with VPC configuration for RDS access
  - ECR repository for epistemix-api Docker images
  - S3 upload bucket with CORS and lifecycle policies
  - SSM bastion for secure database access via port forwarding

### Changed
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

## [2025-10-14]

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
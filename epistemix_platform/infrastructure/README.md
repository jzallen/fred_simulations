# Epistemix Platform Infrastructure

This directory contains AWS CloudFormation templates and Sceptre configurations for deploying the Epistemix platform infrastructure.

## Overview

The infrastructure consists of:
- **RDS PostgreSQL**: Secure private database with SSM bastion access
- **Lambda Function**: Container-based Flask API with VPC integration
- **API Gateway**: REST API with throttling and CORS configuration
- **ECR Repository**: Container registry for API Docker images
- **S3 Upload Bucket**: Secure file upload storage with lifecycle policies
- **SSM Bastion**: EC2 instance for secure RDS access via Session Manager

## Architecture

### Network Security
- RDS is NOT publicly accessible (Private subnets only)
- Lambda runs in VPC private subnets with NAT Gateway for AWS service access
- SSM bastion provides secure database access without SSH keys or public IPs
- Security groups enforce least privilege access

### API Flow
```
Client → API Gateway → Lambda (VPC) → RDS (Private)
                              ↓
                             S3
```

### Database Access
```
Developer → SSM Session Manager → Bastion (VPC) → RDS (Private)
```

## Prerequisites

- AWS CLI v2 configured with appropriate credentials
- Python 3.8 or higher
- Poetry package manager
- Docker (for building container images)
- AWS Session Manager plugin (for RDS access)
- **AWS Secrets Manager secret** containing the database password at path `/epistemix/{Environment}/database/password`

## Installation

### 1. AWS CLI v2

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version  # Should show aws-cli/2.x.x
```

### 2. AWS Session Manager Plugin

```bash
# Debian/Ubuntu
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb

# Verify installation
session-manager-plugin --version
```

### 3. Python Dependencies

```bash
cd epistemix_platform/infrastructure
poetry install
```

## Project Structure

```
infrastructure/
├── config/                 # Sceptre configuration files
│   ├── config.yaml        # Global configuration
│   ├── dev/               # Development environment
│   │   ├── rds-postgres.yaml
│   │   ├── ssm-bastion.yaml
│   │   ├── epistemix-api-lambda.yaml
│   │   └── api-gateway.yaml
│   └── staging/           # Staging environment
├── templates/             # CloudFormation templates
│   ├── rds/              # RDS PostgreSQL
│   ├── bastion/          # SSM bastion
│   ├── lambda/           # Lambda function
│   ├── api-gateway/      # API Gateway
│   ├── ecr/              # Container registry
│   └── s3/               # S3 buckets
└── docs/                 # Additional documentation
```

## Quick Start Deployment

### 1. Create Database Password Secret (One-Time Setup)

The infrastructure expects a database password to exist in AWS Secrets Manager. Create it once manually:

```bash
# Create the secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name "/epistemix/dev/database/password" \
  --description "RDS database password for Epistemix Platform" \
  --secret-string "your-secure-password-here" \
  --region us-east-1

# For production:
# aws secretsmanager create-secret \
#   --name "/epistemix/production/database/password" \
#   --description "RDS database password for Epistemix Platform" \
#   --secret-string "your-production-password" \
#   --region us-east-1
```

**Note**: Both RDS and Lambda stacks use CloudFormation dynamic references (`{{resolve:secretsmanager:...}}`) to retrieve the password at deployment time. You don't need to pass the password as a parameter - CloudFormation reads it directly from Secrets Manager.

To update the password later:
```bash
aws secretsmanager update-secret \
  --secret-id "/epistemix/dev/database/password" \
  --secret-string "new-secure-password" \
  --region us-east-1
```

### 2. Set Environment Variables

```bash
export DEVELOPER_IP="$(curl -s ifconfig.me)/32"
```

### 3. Deploy Core Infrastructure

```bash
cd epistemix_platform/infrastructure

# Deploy RDS database
poetry run sceptre launch dev/rds-postgres.yaml --yes

# Deploy SSM bastion for database access
poetry run sceptre launch dev/ssm-bastion.yaml --yes

# Deploy ECR repository
poetry run sceptre launch dev/epistemix-api-ecr.yaml --yes

# Deploy S3 upload bucket
poetry run sceptre launch dev/s3-upload-bucket.yaml --yes
```

### 3. Build and Push Docker Image

```bash
cd epistemix_platform

# Build with Pants
pants package :epistemix-api-docker

# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  170692816356.dkr.ecr.us-east-1.amazonaws.com

docker tag epistemix-api:latest \
  170692816356.dkr.ecr.us-east-1.amazonaws.com/epistemix-api:latest

docker push 170692816356.dkr.ecr.us-east-1.amazonaws.com/epistemix-api:latest
```

### 4. Deploy API Infrastructure

```bash
cd epistemix_platform/infrastructure

# Deploy Lambda function
poetry run sceptre launch dev/epistemix-api-lambda.yaml --yes

# Deploy API Gateway
poetry run sceptre launch dev/api-gateway.yaml --yes
```

### 5. Get API Gateway URL

```bash
aws cloudformation describe-stacks \
  --stack-name epistemix-api-gateway-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`StageUrl`].OutputValue' \
  --output text
```

## Running Database Migrations

The project includes a `migration-runner` Docker container that uses the bootstrap configuration module to load database credentials from either:
1. Local `.env` file (for development)
2. AWS Parameter Store (for AWS environments)

### Local Development Migrations

```bash
# 1. Create .env file from example
cp .env.example .env

# 2. Edit .env file with your database credentials
# DATABASE_URL=postgresql://epistemix_user:epistemix_password@postgres:5432/epistemix_db

# 3. Start PostgreSQL
docker-compose up -d postgres

# 4. Run migrations
docker-compose run --rm migration-runner alembic upgrade head

# 5. Check migration status
docker-compose run --rm migration-runner alembic current

# 6. Show migration history
docker-compose run --rm migration-runner alembic history
```

### AWS Environment Migrations (with Parameter Store)

The bootstrap module automatically loads configuration from AWS Parameter Store when running in AWS environments.

```bash
# 1. Ensure parameters are set in Parameter Store
# Required parameters under /epistemix/{environment}/:
# - database/host
# - database/port
# - database/name
# - database/user
# - database/password

# 2. Build migration-runner image
pants package //:migration-runner

# 3. Run migrations in AWS (example using ECS/Fargate)
# The ENVIRONMENT variable determines Parameter Store path
docker run --rm \
  -e ENVIRONMENT=production \
  -e AWS_REGION=us-east-1 \
  migration-runner:latest alembic upgrade head
```

### Manual Configuration Override

You can override the bootstrap configuration by providing explicit DATABASE_URL:

```bash
# Override with explicit DATABASE_URL
docker-compose run --rm \
  -e DATABASE_URL=postgresql://user:pass@custom-host:5432/db \
  migration-runner alembic upgrade head

# Test bootstrap is working
docker-compose run --rm migration-runner \
  python3 -c "from epistemix_platform.bootstrap import bootstrap_config; bootstrap_config(); import os; print('DATABASE_URL:', os.environ.get('DATABASE_URL'))"
```

### Migration Entrypoint Behavior

The `migration-entrypoint.sh` script:
1. Calls `bootstrap_config()` to load configuration from .env or Parameter Store
2. Handles postgres:// to postgresql:// URL conversion
3. Waits for database to be available (with timeout)
4. Sets PYTHONPATH for epistemix_platform imports
5. Runs the provided command (default: `alembic --help`)

### Configuration Priority

The bootstrap module uses the following priority order:
1. **Lowest**: Values from `.env` file (if exists)
2. **Medium**: Explicit environment variables (override .env)
3. **Highest**: AWS Parameter Store (fills in missing values)

This means:
- Local development: Use `.env` file
- AWS environments: Parameter Store provides all config
- Override: Set explicit environment variables when needed

### Troubleshooting Migration-Runner

**Bootstrap not loading configuration:**
```bash
# Check if bootstrap module is accessible
docker-compose run --rm migration-runner \
  python3 -c "import epistemix_platform.bootstrap; print('Bootstrap OK')"

# Check what environment is being used
docker-compose run --rm migration-runner \
  python3 -c "import os; print('ENVIRONMENT:', os.getenv('ENVIRONMENT', 'dev'))"
```

**Database connection errors:**
```bash
# Test database connectivity
docker-compose run --rm migration-runner \
  psql "$DATABASE_URL" -c "SELECT version();"

# Check if DATABASE_URL is set after bootstrap
docker-compose run --rm migration-runner \
  bash -c "python3 -c 'from epistemix_platform.bootstrap import bootstrap_config; bootstrap_config()' && echo \$DATABASE_URL"
```

**Parameter Store access denied:**
- Ensure IAM role/user has `ssm:GetParametersByPath` permission
- Verify parameters exist at `/epistemix/{environment}/database/*`
- Check AWS_REGION is set correctly

## Accessing the RDS Database

### Method 1: SSM Port Forwarding (Recommended)

```bash
# Start port forwarding session
aws ssm start-session \
  --target i-BASTION_INSTANCE_ID \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["RDS_ENDPOINT"],"portNumber":["5432"],"localPortNumber":["5432"]}'

# In another terminal, connect to database
# Note: URL-encode special characters in password (! → %21)
psql "postgresql://epistemixuser:PASSWORD%21@localhost:5432/epistemixdb?sslmode=require"
```

### Method 2: Direct Connection (If DeveloperIP configured)

```bash
psql "postgresql://epistemixuser:PASSWORD@RDS_ENDPOINT:5432/epistemixdb"
```

## Testing the Deployment

```bash
# Health check
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/v1/health

# Test job creation
curl -X POST https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/v1/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name": "test-job", "description": "Test"}'
```

## Stack Management

### View Stack Status

```bash
# All stacks in environment
poetry run sceptre status dev

# Specific stack
poetry run sceptre status dev/rds-postgres.yaml
```

### Update a Stack

```bash
poetry run sceptre update dev/rds-postgres.yaml --yes
```

### Delete a Stack

```bash
poetry run sceptre delete dev/rds-postgres.yaml --yes
```

### Validate Templates

```bash
poetry run sceptre validate dev
```

## Security Configuration

### RDS Security Features

- **Private Access**: Database is NOT publicly accessible
- **VPC CIDR Access**: Allows connections from VPC (172.31.0.0/16)
- **Developer IP Access**: Optional developer IP whitelist via `DeveloperIP` parameter
- **Lambda Access**: Lambda security group has access for API operations
- **SSM Bastion Access**: Secure administrative access via Session Manager
- **SSL/TLS Required**: All connections must use encryption

### Security Groups

**RDS Security Group** - Allows inbound on port 5432 from:
- Lambda security group
- Bastion security group
- VPC CIDR (172.31.0.0/16)
- Developer IP (if configured)

**Lambda Security Group** - Allows:
- Outbound HTTPS (443) for AWS services
- Outbound PostgreSQL (5432) to RDS

**Bastion Security Group** - Allows:
- Outbound HTTPS (443) for SSM agent
- Outbound PostgreSQL (5432) to RDS

### API Security

- **CORS**: Configured per environment
- **Throttling**: Environment-specific rate limits
- **Logging**: CloudWatch logs for all requests
- **VPC Integration**: Lambda runs in private subnets

## Monitoring and Observability

### CloudWatch Logs

```bash
# Lambda logs
aws logs tail /aws/lambda/epistemix-api-dev --follow

# API Gateway logs
aws logs tail /aws/apigateway/epistemix-api-dev --follow
```

### Key Metrics

**Lambda**:
- Invocations, Duration, Errors, Throttles
- Cold start times
- Concurrent executions

**API Gateway**:
- Request count
- Latency (4xx/5xx errors)
- Integration latency

**RDS**:
- Database connections
- CPU utilization
- Freeable memory

## Troubleshooting

### Lambda Cannot Connect to RDS

1. Verify Lambda is in private subnets
2. Check RDS security group allows Lambda SG on port 5432
3. Verify DATABASE_URL environment variable is correct
4. Check VPC NAT Gateway for internet access

```bash
# Check Lambda VPC config
aws lambda get-function-configuration \
  --function-name epistemix-api-dev \
  --query 'VpcConfig'

# Check RDS security group
aws ec2 describe-security-groups --group-ids RDS_SG_ID \
  --query 'SecurityGroups[0].IpPermissions'
```

### API Gateway Returns 502 Bad Gateway

1. Check Lambda logs for errors
2. Verify Lambda timeout is sufficient (60s)
3. Check Lambda environment variables
4. Verify ECR image includes Lambda Web Adapter

```bash
aws logs tail /aws/lambda/epistemix-api-dev --since 5m
```

### SSM Port Forwarding Fails

1. Verify SSM agent is running on bastion
2. Check bastion security group allows outbound HTTPS
3. Verify IAM permissions for SSM

```bash
# Check SSM agent status
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-INSTANCE_ID"
```

### Password Authentication Fails

1. Special characters in passwords must be URL-encoded in connection strings
   - `!` → `%21`
   - `@` → `%40`
   - `#` → `%23`
2. Verify password environment variable was set during deployment
3. Try resetting RDS master password

```bash
aws rds modify-db-instance \
  --db-instance-identifier DB_INSTANCE_ID \
  --master-user-password "NewPassword" \
  --apply-immediately
```

## Architectural Decisions

### Lambda Container vs ZIP
- **Choice**: Container-based Lambda
- **Reason**: Better dependency management, no 50MB limit, consistency with local dev

### API Gateway REST vs HTTP
- **Choice**: REST API
- **Reason**: More features (WAF, resource policies, usage plans), better monitoring

### VPC Integration
- **Choice**: Lambda in VPC with private subnets
- **Reason**: Direct RDS access, better security, no public endpoints

### Lambda Configuration
- **Memory**: 3008 MB (≈2 vCPU)
- **Timeout**: 60 seconds
- **Reason**: Balance between performance and cost

### SSM Bastion vs VPN
- **Choice**: SSM bastion with Session Manager
- **Reason**: No VPN infrastructure, no SSH keys, full audit logging, port forwarding support

## Cost Estimates

**Development Environment** (~1000 requests/month):
- Lambda: ~$0.20/month
- API Gateway: ~$3.50/month
- RDS db.t3.micro: ~$15/month
- SSM Bastion t3.nano: ~$3/month
- S3: ~$0.50/month
- NAT Gateway: ~$30/month
- **Total: ~$52/month**

**Production Environment** (~100K requests/month):
- Lambda: ~$20/month
- API Gateway: ~$350/month
- RDS db.t3.medium: ~$60/month
- S3: ~$5/month
- NAT Gateway: ~$30/month
- **Total: ~$465/month**

## Security Best Practices

1. Never use 0.0.0.0/0 for RDS access
2. Regularly rotate database passwords
3. Use IAM roles instead of passwords where possible
4. Enable CloudTrail for API auditing
5. Use encrypted connections (SSL/TLS)
6. Review security group rules quarterly
7. Enable CloudWatch alarms for anomalies
8. Use AWS Secrets Manager for password rotation (future enhancement)

## Additional Resources

- [Sceptre Documentation](https://docs.sceptre-project.org/)
- [AWS CloudFormation Best Practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)
- [AWS Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)

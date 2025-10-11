# API Gateway + Lambda Infrastructure Deployment Guide

## Overview

This document describes the API Gateway + Lambda infrastructure for FRED-29, which replaces the nginx configuration with AWS-native serverless components.

## Architecture

The infrastructure consists of the following components:

1. **Lambda Execution Role** - IAM role with permissions for VPC, RDS, S3, and CloudWatch Logs
2. **Lambda Function** - Container-based Lambda running the Flask application with Lambda Web Adapter
3. **API Gateway REST API** - REST API with 7 endpoints matching the Flask routes
4. **API Gateway Deployment** - Stage deployment with CloudWatch logging
5. **Lambda Permission** - Grants API Gateway permission to invoke Lambda

## API Endpoints

The API Gateway exposes the following endpoints (all proxied to Lambda):

- `GET /health` - Health check endpoint
- `GET /api/v1/registration` - Registration information
- `POST /api/v1/jobs` - Create a new job
- `GET /api/v1/jobs/{job_id}` - Get job details
- `POST /api/v1/runs` - Create a new run
- `GET /api/v1/runs/{run_id}` - Get run details
- `GET /api/v1/runs/{run_id}/upload-url` - Get presigned S3 upload URL
- `ANY /{proxy+}` - Catch-all for other routes

## Prerequisites

### 1. VPC Configuration

You need to identify the VPC subnets for Lambda deployment. Run the following commands:

```bash
# List all VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table

# List subnets in your VPC (replace VPC_ID with your VPC ID)
aws ec2 describe-subnets --filters "Name=vpc-id,Values=VPC_ID" \
  --query 'Subnets[*].[SubnetId,CidrBlock,AvailabilityZone,Tags[?Key==`Name`].Value|[0]]' --output table
```

**Important**: Use private subnets (not public) for Lambda functions connecting to RDS.

### 2. Environment Variables

Set the following environment variables before deployment:

```bash
# Database password for dev environment
export EPISTEMIX_DB_PASSWORD="your-secure-password"

# For staging environment
export EPISTEMIX_DB_HOST_STAGING="your-staging-rds-endpoint"
export EPISTEMIX_DB_PASSWORD_STAGING="your-staging-password"

# For production environment
export EPISTEMIX_DB_HOST_PRODUCTION="your-production-rds-endpoint"
export EPISTEMIX_DB_PASSWORD_PRODUCTION="your-production-password"
```

### 3. Update VPC Subnet IDs

Edit the Lambda function config files and replace placeholder subnet IDs:

- `config/dev/lambda-function.yaml` - Update `VPCSubnetIds`
- `config/staging/lambda-function.yaml` - Update `VPCSubnetIds`
- `config/production/lambda-function.yaml` - Update `VPCSubnetIds`

## Deployment Sequence

### Step 1: Deploy Prerequisites (if not already deployed)

```bash
cd epistemix_platform/infrastructure

# Deploy ECR repository
poetry run sceptre launch dev/ecr.yaml

# Deploy S3 upload bucket
poetry run sceptre launch dev/s3-upload-bucket.yaml

# Deploy RDS database
poetry run sceptre launch dev/rds-postgres.yaml
```

### Step 2: Build and Push Docker Image

```bash
cd epistemix_platform

# Build Docker image with Pants
pants package epistemix_platform:epistemix-api-docker

# Tag and push to ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fred-simulation-runner"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

# Tag and push
docker tag epistemix-api:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest
```

### Step 3: Deploy Lambda Infrastructure

```bash
cd epistemix_platform/infrastructure

# Deploy Lambda execution role
poetry run sceptre launch dev/lambda-execution-role.yaml

# Deploy Lambda function
poetry run sceptre launch dev/lambda-function.yaml

# Note the Lambda Security Group ID from outputs
LAMBDA_SG_ID=$(poetry run sceptre list outputs dev/lambda-function.yaml | grep SecurityGroupId | awk '{print $2}')
echo "Lambda Security Group ID: $LAMBDA_SG_ID"
```

### Step 4: Update RDS Security Group

Update the RDS stack to allow Lambda access:

```bash
# Edit dev/rds-postgres.yaml and add:
# parameters:
#   LambdaSecurityGroupId: "sg-XXXXXXXXX"  # Use the Lambda SG ID from above

# Update the RDS stack
poetry run sceptre update dev/rds-postgres.yaml
```

### Step 5: Deploy API Gateway

```bash
# Deploy API Gateway REST API
poetry run sceptre launch dev/api-gateway.yaml

# Deploy Lambda permission (allows API Gateway to invoke Lambda)
poetry run sceptre launch dev/lambda-permission.yaml

# Deploy API Gateway stage
poetry run sceptre launch dev/api-gateway-deployment.yaml
```

### Step 6: Get API Gateway URL

```bash
# Get the API Gateway URL
poetry run sceptre list outputs dev/api-gateway-deployment.yaml

# Or construct it manually:
API_ID=$(poetry run sceptre list outputs dev/api-gateway.yaml | grep RestApiId | awk '{print $2}')
echo "API Gateway URL: https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/v1"
```

## Testing the Deployment

### 1. Test Health Endpoint

```bash
API_URL=$(poetry run sceptre list outputs dev/api-gateway-deployment.yaml | grep StageUrl | awk '{print $2}')

curl ${API_URL}/health
# Expected: {"status": "healthy"}
```

### 2. Test Registration Endpoint

```bash
curl ${API_URL}/api/v1/registration
# Expected: JSON with registration information
```

### 3. Test Job Creation

```bash
curl -X POST ${API_URL}/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name": "test-job", "description": "Test job"}'
# Expected: JSON with job details
```

## Monitoring and Logs

### CloudWatch Logs

Lambda logs are available in CloudWatch:

```bash
# View Lambda logs
aws logs tail /aws/lambda/epistemix-api-dev --follow

# View API Gateway logs
aws logs tail /aws/apigateway/epistemix-api-dev --follow
```

### API Gateway Metrics

View API Gateway metrics in CloudWatch console:
- Request count
- Latency (4xx, 5xx errors)
- Integration latency
- Cache hit/miss (if caching enabled)

### Lambda Metrics

View Lambda metrics in CloudWatch console:
- Invocations
- Duration
- Errors
- Throttles
- Concurrent executions

## Troubleshooting

### Lambda Cannot Connect to RDS

**Symptoms**: Lambda times out or fails to connect to database

**Solutions**:
1. Verify Lambda is in private subnets
2. Verify RDS security group allows Lambda security group on port 5432
3. Check VPC subnet route tables have NAT gateway for internet access
4. Verify DATABASE_URL environment variable is correct

```bash
# Check Lambda security group
aws ec2 describe-security-groups --group-ids <lambda-sg-id>

# Check RDS security group rules
aws ec2 describe-security-groups --group-ids <rds-sg-id> \
  --query 'SecurityGroups[0].IpPermissions'
```

### API Gateway Returns 502 Bad Gateway

**Symptoms**: API Gateway returns 502 error

**Solutions**:
1. Check Lambda function logs for errors
2. Verify Lambda function has correct environment variables
3. Check Lambda function timeout (increase if needed)
4. Verify ECR image is correct and includes Lambda Web Adapter

```bash
# Check Lambda logs
aws logs tail /aws/lambda/epistemix-api-dev --since 5m
```

### CORS Errors

**Symptoms**: Browser requests fail with CORS errors

**Solutions**:
1. Verify `AllowedOrigins` parameter in API Gateway config
2. Check API Gateway OPTIONS method responses
3. Verify Lambda returns proper CORS headers

## Stack Dependencies

The stacks must be deployed in this order:

1. Prerequisites (ECR, S3, RDS) - can be deployed in parallel
2. Lambda execution role
3. Lambda function
4. Update RDS stack with Lambda security group
5. API Gateway
6. Lambda permission
7. API Gateway deployment

## Cost Estimates

**Development Environment** (low traffic, ~1000 requests/month):
- Lambda: ~$0.20/month (128MB, 1s duration)
- API Gateway: ~$3.50/month (1000 requests)
- RDS db.t3.micro: ~$15/month
- S3: ~$0.50/month
- **Total: ~$19/month**

**Production Environment** (moderate traffic, ~100K requests/month):
- Lambda: ~$20/month (3GB, 1s duration)
- API Gateway: ~$350/month (100K requests)
- RDS db.t3.medium: ~$60/month
- S3: ~$5/month
- **Total: ~$435/month**

Note: Costs assume 1-second average Lambda duration and moderate data transfer.

## Cleanup

To delete all stacks (in reverse order):

```bash
cd epistemix_platform/infrastructure

# Delete API Gateway deployment
poetry run sceptre delete dev/api-gateway-deployment.yaml

# Delete Lambda permission
poetry run sceptre delete dev/lambda-permission.yaml

# Delete API Gateway
poetry run sceptre delete dev/api-gateway.yaml

# Delete Lambda function
poetry run sceptre delete dev/lambda-function.yaml

# Delete Lambda execution role
poetry run sceptre delete dev/lambda-execution-role.yaml
```

## Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)
- [Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter)
- [Sceptre Documentation](https://sceptre.cloudreach.com/)

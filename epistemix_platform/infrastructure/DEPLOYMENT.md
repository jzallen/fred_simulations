# Epistemix API Infrastructure Deployment Guide

This guide covers deploying the Epistemix API serverless infrastructure using Sceptre.

## Prerequisites

1. **AWS Credentials**: Configured with appropriate permissions
2. **Poetry**: For dependency management
3. **Docker**: For building and pushing container images
4. **Existing Infrastructure**: ECR, RDS, and S3 stacks must exist

## Required AWS Permissions

To deploy the Lambda and API Gateway infrastructure, you need the following IAM permissions:

### IAM Permissions
- `iam:CreateRole`
- `iam:PutRolePolicy`
- `iam:AttachRolePolicy`
- `iam:TagRole`
- `iam:GetRole`
- `iam:PassRole`

### Lambda Permissions
- `lambda:CreateFunction`
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:TagResource`
- `lambda:PublishVersion`
- `lambda:CreateAlias`

### API Gateway Permissions
- `apigateway:*` (or specific permissions for creating REST APIs, resources, methods, deployments, stages)

### EC2 Permissions (for VPC Lambda)
- `ec2:CreateSecurityGroup`
- `ec2:DescribeSecurityGroups`
- `ec2:AuthorizeSecurityGroupIngress`
- `ec2:AuthorizeSecurityGroupEgress`
- `ec2:CreateTags`
- `ec2:DescribeSubnets`
- `ec2:DescribeVpcs`

### CloudWatch Logs Permissions
- `logs:CreateLogGroup`
- `logs:PutRetentionPolicy`
- `logs:TagResource`

### ECR Permissions
- `ecr:CreateRepository`
- `ecr:PutLifecyclePolicy`
- `ecr:TagResource`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`
- `ecr:PutImage`

## Deployment Steps

### 1. Install Dependencies

```bash
cd epistemix_platform/infrastructure
poetry install
```

### 2. Set Environment Variables

```bash
export EPISTEMIX_DB_PASSWORD="your-secure-password"
```

### 3. Deploy ECR Repository (if not exists)

```bash
poetry run sceptre launch dev/epistemix-api-ecr.yaml --yes
```

### 4. Build and Push Docker Image

```bash
# Navigate to epistemix_platform directory
cd /workspaces/fred_simulations/epistemix_platform

# Build Docker image using Pants
pants package :epistemix-api-docker

# Tag and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 170692816356.dkr.ecr.us-east-1.amazonaws.com
docker tag epistemix-api:latest 170692816356.dkr.ecr.us-east-1.amazonaws.com/epistemix-api:latest
docker push 170692816356.dkr.ecr.us-east-1.amazonaws.com/epistemix-api:latest
```

### 5. Deploy Lambda Stack

```bash
cd infrastructure
export EPISTEMIX_DB_PASSWORD="your-password"
poetry run sceptre launch dev/epistemix-api-lambda.yaml --yes
```

### 6. Deploy API Gateway Stack

```bash
poetry run sceptre launch dev/api-gateway.yaml --yes
```

### 7. Update Lambda with API Gateway Permission (Optional)

After API Gateway is created, update the Lambda config to add the API Gateway ID for the invoke permission:

```yaml
# In config/dev/epistemix-api-lambda.yaml
ApiGatewayRestApiId: "!stack_output_external epistemix-api-gateway-dev::RestApiId"
```

Then update the stack:

```bash
poetry run sceptre update dev/epistemix-api-lambda.yaml --yes
```

### 8. Update RDS Security Group

Update the RDS stack to allow Lambda security group access:

```bash
# Get Lambda security group ID
aws cloudformation describe-stacks --stack-name epistemix-api-lambda-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`SecurityGroupId`].OutputValue' --output text

# Update RDS stack parameter with Lambda SG ID
# (This requires updating the RDS stack configuration)
```

## Testing

Get the API Gateway endpoint URL:

```bash
aws cloudformation describe-stacks --stack-name epistemix-api-gateway-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`StageUrl`].OutputValue' --output text
```

Test the health endpoint:

```bash
curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/v1/health
```

## Troubleshooting

### Permission Errors

If you get IAM permission errors, ensure your AWS user/role has all required permissions listed above.

### VPC Configuration

Ensure:
- Lambda is deployed in private subnets
- Private subnets have a route to NAT Gateway for external AWS service access
- Security groups allow Lambda → RDS communication on port 5432

### Docker Build Issues

If Docker build fails:
- Check that the Dockerfile exists in epistemix_platform/
- Ensure Lambda Web Adapter is properly configured
- Verify all Python dependencies are in pyproject.toml

## Stack Management

List all stacks:
```bash
poetry run sceptre list stacks dev
```

Delete a stack:
```bash
poetry run sceptre delete dev/STACK-NAME.yaml --yes
```

Update a stack:
```bash
poetry run sceptre update dev/STACK-NAME.yaml --yes
```

## Infrastructure Overview

**Deployed Stacks (per environment):**
1. epistemix-api-ecr - ECR repository for container images
2. epistemix-api-lambda - Lambda function with IAM role, security group, logs
3. epistemix-api-gateway - API Gateway REST API with deployment and stage

**External Dependencies:**
- fred-simulations-dev-rds-postgres (RDS PostgreSQL database)
- epistemix-uploads-dev-stack (S3 bucket for uploads)
- VPC with private subnets and NAT Gateway

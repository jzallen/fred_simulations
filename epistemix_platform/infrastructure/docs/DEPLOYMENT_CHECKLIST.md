# Deployment Checklist for API Gateway + Lambda Infrastructure

## Pre-Deployment Checklist

### 1. VPC and Network Configuration

- [ ] Identify VPC ID to use for deployment
- [ ] Identify private subnet IDs (minimum 2 for high availability)
- [ ] Verify NAT Gateway exists in VPC for Lambda internet access
- [ ] Confirm route tables for private subnets route to NAT Gateway
- [ ] Document subnet IDs in deployment notes

**Commands**:
```bash
# List VPCs
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table

# List private subnets
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<VPC_ID>" \
  --query 'Subnets[?MapPublicIpOnLaunch==`false`].[SubnetId,CidrBlock,AvailabilityZone]' --output table
```

### 2. Environment Variables

- [ ] Set EPISTEMIX_DB_PASSWORD for dev environment
- [ ] Set EPISTEMIX_DB_HOST_STAGING and EPISTEMIX_DB_PASSWORD_STAGING (if deploying staging)
- [ ] Set EPISTEMIX_DB_HOST_PRODUCTION and EPISTEMIX_DB_PASSWORD_PRODUCTION (if deploying production)
- [ ] Verify environment variables are exported in shell

**Commands**:
```bash
export EPISTEMIX_DB_PASSWORD="<secure-password>"
echo $EPISTEMIX_DB_PASSWORD  # Verify it's set
```

### 3. Update Configuration Files

- [ ] Edit `config/dev/lambda-function.yaml` and update `VPCSubnetIds`
- [ ] Edit `config/staging/lambda-function.yaml` and update `VPCSubnetIds` (if deploying)
- [ ] Edit `config/production/lambda-function.yaml` and update `VPCSubnetIds` (if deploying)
- [ ] Verify CORS origins in `api-gateway.yaml` files are correct

### 4. Prerequisites Deployed

- [ ] ECR repository deployed (`dev/ecr.yaml`)
- [ ] S3 upload bucket deployed (`dev/s3-upload-bucket.yaml`)
- [ ] RDS database deployed (`dev/rds-postgres.yaml`)
- [ ] Docker image built and pushed to ECR

**Verification**:
```bash
cd epistemix_platform/infrastructure

# Check if stacks exist
poetry run sceptre list outputs dev/ecr.yaml
poetry run sceptre list outputs dev/s3-upload-bucket.yaml
poetry run sceptre list outputs dev/rds-postgres.yaml
```

### 5. Docker Image Ready

- [ ] Docker image built with Pants or Docker CLI
- [ ] Image tagged correctly for ECR
- [ ] Image pushed to ECR repository
- [ ] Verify image exists in ECR console or CLI

**Commands**:
```bash
# Build image (from epistemix_platform directory)
cd epistemix_platform
pants package epistemix_platform:epistemix-api-docker

# Tag and push
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fred-simulation-runner"

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}

docker tag epistemix-api:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest
```

## Deployment Steps

### Phase 1: Lambda Infrastructure

- [ ] Deploy Lambda execution role
  ```bash
  cd epistemix_platform/infrastructure
  poetry run sceptre launch dev/lambda-execution-role.yaml
  ```

- [ ] Verify role created successfully
  ```bash
  poetry run sceptre list outputs dev/lambda-execution-role.yaml
  ```

- [ ] Deploy Lambda function
  ```bash
  poetry run sceptre launch dev/lambda-function.yaml
  ```

- [ ] Verify Lambda function created
  ```bash
  poetry run sceptre list outputs dev/lambda-function.yaml
  ```

- [ ] Get Lambda Security Group ID
  ```bash
  LAMBDA_SG_ID=$(poetry run sceptre list outputs dev/lambda-function.yaml | grep SecurityGroupId | awk '{print $2}')
  echo "Lambda SG: $LAMBDA_SG_ID"
  ```

### Phase 2: Update RDS Security Group

- [ ] Edit `config/dev/rds-postgres.yaml`
- [ ] Add parameter: `LambdaSecurityGroupId: "<LAMBDA_SG_ID>"`
- [ ] Update RDS stack
  ```bash
  poetry run sceptre update dev/rds-postgres.yaml
  ```

- [ ] Verify RDS security group updated
  ```bash
  RDS_SG_ID=$(poetry run sceptre list outputs dev/rds-postgres.yaml | grep SecurityGroupId | awk '{print $2}')
  aws ec2 describe-security-groups --group-ids $RDS_SG_ID --query 'SecurityGroups[0].IpPermissions'
  ```

### Phase 3: API Gateway

- [ ] Deploy API Gateway
  ```bash
  poetry run sceptre launch dev/api-gateway.yaml
  ```

- [ ] Verify API Gateway created
  ```bash
  poetry run sceptre list outputs dev/api-gateway.yaml
  ```

- [ ] Deploy Lambda permission
  ```bash
  poetry run sceptre launch dev/lambda-permission.yaml
  ```

- [ ] Deploy API Gateway deployment
  ```bash
  poetry run sceptre launch dev/api-gateway-deployment.yaml
  ```

- [ ] Get API Gateway URL
  ```bash
  API_URL=$(poetry run sceptre list outputs dev/api-gateway-deployment.yaml | grep StageUrl | awk '{print $2}')
  echo "API Gateway URL: $API_URL"
  ```

## Post-Deployment Verification

### 1. Test Health Endpoint

- [ ] Test health endpoint returns 200 OK
  ```bash
  curl -i ${API_URL}/health
  # Expected: HTTP/1.1 200 OK
  # Body: {"status": "healthy"}
  ```

### 2. Test Registration Endpoint

- [ ] Test registration endpoint returns valid JSON
  ```bash
  curl -i ${API_URL}/api/v1/registration
  # Expected: HTTP/1.1 200 OK
  # Body: JSON with registration data
  ```

### 3. Test Database Connectivity

- [ ] Test endpoint that queries database (jobs/runs)
  ```bash
  curl -X POST ${API_URL}/api/v1/jobs \
    -H "Content-Type: application/json" \
    -d '{"name": "test-job", "description": "Test"}'
  # Expected: HTTP/1.1 201 Created
  # Body: JSON with job details
  ```

### 4. Test S3 Integration

- [ ] Test upload URL generation
  ```bash
  # First create a run
  RUN_RESPONSE=$(curl -X POST ${API_URL}/api/v1/runs \
    -H "Content-Type: application/json" \
    -d '{"job_id": 1, "config": {}}')

  RUN_ID=$(echo $RUN_RESPONSE | jq -r '.id')

  # Get upload URL
  curl ${API_URL}/api/v1/runs/${RUN_ID}/upload-url
  # Expected: JSON with presigned S3 URL
  ```

### 5. Check CloudWatch Logs

- [ ] Verify Lambda logs are being written
  ```bash
  aws logs tail /aws/lambda/epistemix-api-dev --since 5m
  ```

- [ ] Verify API Gateway logs are being written
  ```bash
  aws logs tail /aws/apigateway/epistemix-api-dev --since 5m
  ```

### 6. Check CloudWatch Metrics

- [ ] Open CloudWatch console
- [ ] Navigate to Lambda metrics
- [ ] Verify Invocations, Duration, Errors metrics are updating
- [ ] Navigate to API Gateway metrics
- [ ] Verify Count, Latency, 4xx/5xx metrics are updating

## Troubleshooting Checklist

### Lambda Function Errors

- [ ] Check Lambda logs for error messages
  ```bash
  aws logs tail /aws/lambda/epistemix-api-dev --since 10m --follow
  ```

- [ ] Verify environment variables are set correctly
  ```bash
  aws lambda get-function-configuration --function-name epistemix-api-dev \
    --query 'Environment.Variables'
  ```

- [ ] Check Lambda execution role has correct permissions
  ```bash
  aws iam get-role --role-name epistemix-api-lambda-role-dev
  ```

### Database Connection Issues

- [ ] Verify Lambda is in correct VPC subnets
  ```bash
  aws lambda get-function-configuration --function-name epistemix-api-dev \
    --query 'VpcConfig'
  ```

- [ ] Check Lambda security group allows outbound on 5432
  ```bash
  aws ec2 describe-security-groups --group-ids <lambda-sg-id> \
    --query 'SecurityGroups[0].IpPermissionsEgress'
  ```

- [ ] Check RDS security group allows inbound from Lambda SG
  ```bash
  aws ec2 describe-security-groups --group-ids <rds-sg-id> \
    --query 'SecurityGroups[0].IpPermissions'
  ```

- [ ] Verify DATABASE_URL environment variable is correct
  ```bash
  aws lambda get-function-configuration --function-name epistemix-api-dev \
    --query 'Environment.Variables.DATABASE_URL'
  ```

### API Gateway 502 Errors

- [ ] Check Lambda logs for application errors
- [ ] Verify Lambda function timeout is sufficient (60s)
- [ ] Check API Gateway integration configuration
- [ ] Verify Lambda permission allows API Gateway invocation
  ```bash
  aws lambda get-policy --function-name epistemix-api-dev
  ```

### CORS Issues

- [ ] Verify OPTIONS method exists for endpoints
- [ ] Check CORS headers in API Gateway configuration
- [ ] Test preflight request manually
  ```bash
  curl -X OPTIONS ${API_URL}/health \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" -v
  ```

## Rollback Procedure

If deployment fails or issues are discovered:

### Quick Rollback (API Gateway)

- [ ] Revert to previous API Gateway deployment
  ```bash
  # Get previous deployment ID from CloudFormation console
  aws apigateway update-stage --rest-api-id <api-id> \
    --stage-name v1 --patch-operations op=replace,path=/deploymentId,value=<old-deployment-id>
  ```

### Full Rollback

- [ ] Delete API Gateway deployment
  ```bash
  poetry run sceptre delete dev/api-gateway-deployment.yaml
  ```

- [ ] Delete Lambda permission
  ```bash
  poetry run sceptre delete dev/lambda-permission.yaml
  ```

- [ ] Delete API Gateway
  ```bash
  poetry run sceptre delete dev/api-gateway.yaml
  ```

- [ ] Delete Lambda function
  ```bash
  poetry run sceptre delete dev/lambda-function.yaml
  ```

- [ ] Delete Lambda execution role
  ```bash
  poetry run sceptre delete dev/lambda-execution-role.yaml
  ```

- [ ] Revert RDS security group changes
  ```bash
  # Edit config/dev/rds-postgres.yaml and remove LambdaSecurityGroupId parameter
  poetry run sceptre update dev/rds-postgres.yaml
  ```

## Post-Deployment Tasks

- [ ] Update documentation with actual API Gateway URL
- [ ] Configure CloudWatch alarms for monitoring
- [ ] Set up SNS topics for alarm notifications
- [ ] Document any configuration changes or issues encountered
- [ ] Update team wiki/confluence with deployment notes
- [ ] Schedule regular review of CloudWatch logs and metrics

## Notes

- Deployment time: ~10-15 minutes for full stack
- Lambda cold start: ~2-3 seconds (first request)
- Lambda warm start: ~50-200ms (subsequent requests)
- API Gateway + Lambda latency: ~100-300ms (p50)

## Sign-Off

Deployment completed by: ________________

Date: ________________

Environment: [ ] dev [ ] staging [ ] production

API Gateway URL: ________________________________

Issues encountered: _____________________________

_________________________________________________

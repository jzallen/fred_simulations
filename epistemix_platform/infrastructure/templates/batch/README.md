# AWS Batch Infrastructure for FRED Simulations

This directory contains CloudFormation templates and Sceptre configurations for deploying AWS Batch infrastructure to run FRED simulations in the cloud.

## Overview

The AWS Batch infrastructure enables running FRED simulations as containerized batch jobs with the following features:

- **Cost-Effective Compute**: EC2 SPOT instances provide 60-70% cost savings compared to On-Demand
- **Auto-Scaling**: Compute environment scales from 0 to 256 vCPUs based on demand
- **Fault Tolerance**: Automatic retry on Spot instance interruptions
- **Secure**: Least-privilege IAM roles, encrypted secrets, VPC isolation
- **Observable**: CloudWatch Logs integration for debugging

## Architecture

### Infrastructure Components

1. **IAM Roles** (4 separate roles following least-privilege principle):
   - **BatchServiceRole**: AWS Batch service permissions
   - **BatchInstanceRole**: EC2 instance ECS agent permissions
   - **BatchExecutionRole**: Container image pull, logs, secrets access
   - **BatchJobRole**: Application-level permissions (S3, database, secrets)

2. **Compute Environment**:
   - Type: EC2 SPOT instances
   - Instance types: c5.xlarge (4 vCPU, 8 GB), c5.2xlarge (8 vCPU, 16 GB)
   - Allocation strategy: SPOT_CAPACITY_OPTIMIZED
   - Scaling: 0-256 vCPUs (scales to zero when idle)

3. **Job Queue**:
   - Priority: 1
   - State: ENABLED
   - Links jobs to compute environment

4. **Job Definition**:
   - Platform: EC2 (not Fargate)
   - Resources: 4 vCPUs, 8192 MB memory per job
   - Retry strategy: 3 attempts with Spot interruption handling
   - Timeout: 4 hours per attempt
   - Logs: CloudWatch Logs integration

5. **Security Group**:
   - Outbound HTTPS (port 443): S3, ECR, Secrets Manager access
   - Outbound PostgreSQL (port 5432): Database access

6. **CloudWatch Log Group**:
   - Name: `/aws/batch/fred-simulations-{environment}`
   - Retention: Configurable (default 7 days for dev)

### Design Decisions

Based on ENGINEER-01's prototype learnings (see `/tmp/FRED-45/ENGINEER-01/LEARNINGS.md`):

- **Job/Run Mapping**: 1 AWS Batch Job = 1 FredRun (ADR-001)
  - Fine-grained status tracking per run
  - Easier to retry individual failed runs
  - Better CloudWatch Logs separation

- **Compute Environment**: EC2 SPOT (ADR-003)
  - 70% cost savings vs On-Demand
  - c5 instances are compute-optimized for FRED simulations
  - Acceptable interruption risk with retry logic

- **IAM Roles**: 4 separate roles (ADR-004)
  - Clear separation of concerns
  - Least-privilege access
  - Job role can only read uploads, write results
  - Execution role can only pull images and write logs

## CloudFormation Template

**File**: `batch-infrastructure.json`

### Parameters

| Parameter | Description | Default | Notes |
|-----------|-------------|---------|-------|
| `Environment` | Environment name | `dev` | dev/staging/production |
| `VpcId` | VPC ID | Required | VPC where compute environment launches |
| `SubnetIds` | Private subnet IDs | Required | Should have NAT gateway |
| `ECRRepositoryUri` | ECR repository URI | Required | simulation-runner Docker image |
| `DatabaseSecretArn` | Secrets Manager ARN | Required | Database credentials |
| `UploadBucketName` | S3 uploads bucket | Required | Input files for jobs |
| `ResultsBucketName` | S3 results bucket | Required | Output files from simulations |
| `MaxvCpus` | Max vCPUs | `256` | ~64 concurrent c5.xlarge jobs |
| `LogRetentionDays` | CloudWatch logs retention | `7` | 1, 3, 5, 7, 14, 30, 60, 90, etc. |
| `SpotBidPercentage` | Spot bid % of On-Demand | `100` | 100 = use Spot whenever available |

### Resources Created

- 4 IAM Roles (Service, Instance, Execution, Job)
- 1 IAM Instance Profile
- 1 Security Group
- 1 CloudWatch Log Group
- 1 Batch Compute Environment
- 1 Batch Job Queue
- 1 Batch Job Definition

### Outputs

| Output | Description | Export Name |
|--------|-------------|-------------|
| `BatchServiceRoleArn` | Service role ARN | `{StackName}-ServiceRoleArn` |
| `BatchInstanceRoleArn` | Instance role ARN | `{StackName}-InstanceRoleArn` |
| `BatchExecutionRoleArn` | Execution role ARN | `{StackName}-ExecutionRoleArn` |
| `BatchJobRoleArn` | Job role ARN | `{StackName}-JobRoleArn` |
| `BatchSecurityGroupId` | Security group ID | `{StackName}-SecurityGroupId` |
| `BatchLogGroupName` | CloudWatch log group | `{StackName}-LogGroupName` |
| `BatchComputeEnvironmentArn` | Compute environment ARN | `{StackName}-ComputeEnvironmentArn` |
| `BatchJobQueueArn` | Job queue ARN | `{StackName}-JobQueueArn` |
| `BatchJobQueueName` | Job queue name | `{StackName}-JobQueueName` |
| `BatchJobDefinitionArn` | Job definition ARN | `{StackName}-JobDefinitionArn` |

## Sceptre Configuration

**File**: `config/dev/batch-infrastructure.yaml`

### Dependencies

The stack depends on:
1. `dev/database-secrets.yaml`: Database credentials in Secrets Manager
2. `dev/s3-upload-bucket.yaml`: S3 bucket for job uploads
3. `docker-images/simulation-runner-ecr.yaml`: ECR repository for Docker image

### Stack Outputs Used

- `docker-images/simulation-runner-ecr.yaml::RepositoryUri` → `ECRRepositoryUri`
- `dev/database-secrets.yaml::SecretArn` → `DatabaseSecretArn`
- `dev/s3-upload-bucket.yaml::BucketName` → `UploadBucketName`

## Deployment

### Prerequisites

1. VPC with private subnets and NAT gateway
2. Database secret in Secrets Manager
3. S3 upload bucket created
4. ECR repository with simulation-runner Docker image
5. Results S3 bucket created (or update config to create it)

### Deploy with Sceptre

```bash
# Navigate to infrastructure directory
cd epistemix_platform/infrastructure

# Validate the template
sceptre validate dev/batch-infrastructure.yaml

# Deploy the stack
sceptre create dev/batch-infrastructure.yaml

# Check stack status
sceptre status dev/batch-infrastructure.yaml

# View stack outputs
sceptre list outputs dev/batch-infrastructure.yaml
```

### Deploy with AWS CLI

```bash
# Validate template
aws cloudformation validate-template \
  --template-body file://templates/batch/batch-infrastructure.json

# Create stack
aws cloudformation create-stack \
  --stack-name fred-batch-infrastructure-dev \
  --template-body file://templates/batch/batch-infrastructure.json \
  --parameters file://config/dev/batch-infrastructure-params.json \
  --capabilities CAPABILITY_NAMED_IAM
```

## Environment Variables

After deploying the stack, set these environment variables for the application:

```bash
# Get outputs from CloudFormation
JOB_DEFINITION_ARN=$(aws cloudformation describe-stacks \
  --stack-name fred-batch-infrastructure-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`BatchJobDefinitionArn`].OutputValue' \
  --output text)

JOB_QUEUE_NAME=$(aws cloudformation describe-stacks \
  --stack-name fred-batch-infrastructure-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`BatchJobQueueName`].OutputValue' \
  --output text)

# Export for application use
export AWS_BATCH_JOB_DEFINITION=$JOB_DEFINITION_ARN
export AWS_BATCH_JOB_QUEUE=$JOB_QUEUE_NAME
```

The `simulation_runner.py` gateway uses these environment variables:
- `AWS_BATCH_JOB_DEFINITION`: Job definition ARN from CloudFormation output
- `AWS_BATCH_JOB_QUEUE`: Job queue name from CloudFormation output

## Testing

### Template Validation Tests

Run the template validation tests:

```bash
# Run all batch infrastructure tests
pants test epistemix_platform/infrastructure/tests/batch/

# Run specific test
pants test epistemix_platform/infrastructure/tests/batch/test_batch_infrastructure_template.py
```

Tests verify:
- Template is valid JSON
- All required parameters defined
- IAM roles have correct trust policies
- Compute environment uses SPOT instances
- Job definition configures resources correctly
- Security group allows required egress
- All outputs are exported

### Integration Testing

After deploying the stack:

1. **Submit a test job**:
   ```python
   from epistemix_platform.gateways.simulation_runner import create_simulation_runner
   from epistemix_platform.models import Run

   runner = create_simulation_runner()
   run = Run(job_id=1, id=1, ...)  # Create a test run
   runner.submit_run(run)
   ```

2. **Check job status**:
   ```bash
   aws batch describe-jobs --jobs <job-id>
   ```

3. **View logs**:
   ```bash
   aws logs tail /aws/batch/fred-simulations-dev --follow
   ```

## Cost Estimation

Based on ENGINEER-01's cost analysis:

**Assumptions**:
- 100 runs per day
- Average runtime: 30 minutes per run
- Instance type: c5.xlarge (4 vCPU, 8 GB)

**EC2 SPOT (Recommended)**:
- Cost per hour: ~$0.05 (70% discount from On-Demand $0.17)
- Cost per run: ~$0.025
- Daily cost: $2.50 (100 runs)
- **Monthly cost: ~$75**

**EC2 On-Demand (Fallback)**:
- Cost per hour: $0.17
- Cost per run: ~$0.085
- Monthly cost: ~$255

**Expected cost**: $75-100/month with SPOT + occasional On-Demand fallback

## Security

### Least Privilege IAM

Each role has minimal permissions:
- **Service Role**: Batch service management only
- **Instance Role**: ECS agent, CloudWatch Logs
- **Execution Role**: ECR pull, CloudWatch Logs, Secrets Manager read
- **Job Role**: S3 read (uploads), S3 write (results), Secrets Manager read (database)

### Network Isolation

- Compute instances in private subnets (no direct internet access)
- NAT gateway for outbound HTTPS (ECR, S3, Secrets Manager)
- Security group restricts egress to required ports only

### Secrets Management

- Database credentials stored in AWS Secrets Manager
- Automatic encryption at rest
- Access via IAM role (no hardcoded credentials)

### Logging

- All job output sent to CloudWatch Logs
- CloudTrail logs all IAM actions
- VPC Flow Logs can be enabled for network traffic

## Troubleshooting

### Jobs stuck in PENDING

**Cause**: Insufficient compute capacity or invalid instance role.

**Solution**:
1. Check compute environment state: `aws batch describe-compute-environments`
2. Verify instance role has ECS permissions
3. Check subnet has NAT gateway for outbound access

### Jobs fail immediately (FAILED)

**Cause**: Invalid job definition, missing Docker image, or container errors.

**Solution**:
1. Check CloudWatch Logs: `aws logs tail /aws/batch/fred-simulations-dev`
2. Verify ECR image exists and is accessible
3. Check execution role has ECR pull permissions

### Spot instance interruptions

**Cause**: AWS reclaiming Spot capacity.

**Solution**:
- Jobs automatically retry (up to 3 attempts)
- Monitor retry metrics in CloudWatch
- Consider increasing On-Demand fallback if interruptions are frequent

## References

- **ENGINEER-01 Learnings**: `/tmp/FRED-45/ENGINEER-01/LEARNINGS.md`
- **ADR-001**: Job/Run Mapping (1 Batch Job = 1 Run)
- **ADR-003**: Compute Environment Configuration (EC2 SPOT)
- **ADR-004**: IAM Roles and Permissions

- **AWS Batch Documentation**: https://docs.aws.amazon.com/batch/
- **AWS Batch IAM**: https://docs.aws.amazon.com/batch/latest/userguide/IAM_policies.html
- **Spot Best Practices**: https://aws.amazon.com/ec2/spot/getting-started/

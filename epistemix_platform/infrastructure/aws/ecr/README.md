# ECR Repository Infrastructure Deployment

This directory contains the CloudFormation template and parameter files for deploying the FRED Simulation Runner ECR repository.

## Overview

The `simulation-runner-repository.yaml` template creates:
- ECR repository named "fred-simulation-runner" with AWS managed KMS encryption
- Automatic vulnerability scanning on push
- Lifecycle policies for image retention
- IAM roles for different access patterns:
  - CI/CD pipeline role (read/write access)
  - EKS role using IRSA (IAM Roles for Service Accounts)
  - EC2 instance role and profile (read-only access)
- CloudWatch dashboard for monitoring
- CloudWatch logs (optional)

## Prerequisites

1. **AWS CLI configured with appropriate permissions**
2. **Poetry installed for dependency management**
3. **EKS cluster with OIDC provider configured** (for EKS access)

## Deployment Instructions

### Environment-specific Parameter Files

Three parameter files are provided:
- `parameters-dev.json` - Development environment
- `parameters-staging.json` - Staging environment  
- `parameters-production.json` - Production environment

### Deploy the Stack

Choose the appropriate environment and deploy:

```bash
# Development environment
poetry run aws cloudformation deploy \
  --template-file simulation-runner-repository.yaml \
  --stack-name fred-ecr-repository-dev \
  --parameter-overrides file://parameters-dev.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Staging environment
poetry run aws cloudformation deploy \
  --template-file simulation-runner-repository.yaml \
  --stack-name fred-ecr-repository-staging \
  --parameter-overrides file://parameters-staging.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Production environment
poetry run aws cloudformation deploy \
  --template-file simulation-runner-repository.yaml \
  --stack-name fred-ecr-repository-production \
  --parameter-overrides file://parameters-production.json \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Validate Template Before Deployment

```bash
poetry run cfn-lint simulation-runner-repository.yaml
poetry run aws cloudformation validate-template --template-body file://simulation-runner-repository.yaml
```

## Access Patterns

### 1. GitHub Actions CI/CD Pipeline

The CI/CD role provides full read/write access to the ECR repository for GitHub Actions.

**Usage Example:**
```yaml
# In your GitHub Actions workflow
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v2
  with:
    role-to-assume: ${{ secrets.AWS_ROLE_ARN }}  # Use CICDRoleArn from stack outputs
    aws-region: us-east-1

- name: Login to Amazon ECR
  id: login-ecr
  uses: aws-actions/amazon-ecr-login@v1

- name: Build and push Docker image
  run: |
    docker build -t $ECR_REGISTRY/fred-simulation-runner:$GITHUB_SHA .
    docker push $ECR_REGISTRY/fred-simulation-runner:$GITHUB_SHA
```

### 2. EKS Pods (Primary Use Case)

Uses IAM Roles for Service Accounts (IRSA) for secure, keyless access.

**Prerequisites:**
1. EKS cluster with OIDC provider configured
2. ServiceAccount configured with the ECR role annotation

**Setup ServiceAccount:**
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: fred-simulation-runner
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: <EKSRoleArn-from-stack-outputs>
```

**Pod Specification:**
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: fred-simulation-runner
  namespace: default
spec:
  serviceAccountName: fred-simulation-runner
  containers:
  - name: simulation-runner
    image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/fred-simulation-runner:latest
    # Container will automatically have ECR pull permissions via IRSA
```

**Deployment Example:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fred-simulation-runner
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fred-simulation-runner
  template:
    metadata:
      labels:
        app: fred-simulation-runner
    spec:
      serviceAccountName: fred-simulation-runner
      containers:
      - name: fred-simulation-runner
        image: <account-id>.dkr.ecr.us-east-1.amazonaws.com/fred-simulation-runner:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

### 3. EC2 Instances

Uses IAM instance profiles for EC2 instances to pull images.

**Launch Instance with Profile:**
```bash
# Using AWS CLI
poetry run aws ec2 run-instances \
  --image-id ami-12345678 \
  --instance-type t3.medium \
  --iam-instance-profile Name=<EC2InstanceProfileArn-from-stack-outputs> \
  --security-group-ids sg-12345678 \
  --subnet-id subnet-12345678
```

**Docker Commands on EC2:**
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Pull image
docker pull <account-id>.dkr.ecr.us-east-1.amazonaws.com/fred-simulation-runner:latest

# Run container
docker run -d --name fred-runner <account-id>.dkr.ecr.us-east-1.amazonaws.com/fred-simulation-runner:latest
```

## Image Lifecycle Management

The repository includes lifecycle policies to automatically manage images:

1. **Keep last 10 images** tagged as 'latest' or 'main'
2. **Keep last 20 images** with semantic version tags (v1.0.0, etc)
3. **Keep last 5 images** tagged with branch names or 'dev-*'
4. **Delete untagged images** after 1 day
5. **Delete images older than 90 days** unless they match retention rules

## Monitoring and Observability

### CloudWatch Dashboard

The template creates a CloudWatch dashboard with metrics for:
- Repository pull count
- Repository push count  
- Image count
- Image size

Access via stack outputs: `DashboardUrl`

### CloudWatch Logs

ECR events are logged to CloudWatch Logs (if enabled):
- Log Group: `/aws/ecr/fred-simulation-runner`
- Retention: 30 days (dev/staging), 90 days (production)

### Image Scanning

Automatic vulnerability scanning is enabled on image push. Results are available in:
- AWS Console: ECR → Repositories → fred-simulation-runner → Images
- AWS CLI: `poetry run aws ecr describe-image-scan-findings --repository-name fred-simulation-runner`

## Security Features

1. **Encryption at Rest:** AWS managed KMS encryption
2. **Vulnerability Scanning:** Automatic on push
3. **IAM Least Privilege:** Separate roles for different access patterns
4. **Network Security:** ECR endpoints support VPC endpoints for private access
5. **Audit Logging:** CloudTrail logs all ECR API calls

## Troubleshooting

### Common Issues

1. **EKS IRSA Setup:**
   ```bash
   # Verify OIDC provider exists
   poetry run aws iam list-open-id-connect-providers
   
   # Check ServiceAccount annotation
   kubectl describe sa fred-simulation-runner -n default
   ```

2. **EC2 Instance Profile:**
   ```bash
   # Verify instance has profile attached
   poetry run aws ec2 describe-instances --instance-ids i-1234567890abcdef0
   
   # Check instance metadata
   curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
   ```

3. **Image Pull Errors:**
   ```bash
   # Test ECR authentication
   poetry run aws ecr get-authorization-token
   
   # Test repository access
   poetry run aws ecr describe-repositories --repository-names fred-simulation-runner
   ```

## Stack Outputs

After deployment, the following outputs are available:

- `RepositoryName`: ECR repository name
- `RepositoryArn`: ECR repository ARN
- `RepositoryUri`: ECR repository URI for docker commands
- `RegistryId`: AWS Account ID
- `CICDRoleArn`: IAM role ARN for CI/CD pipelines
- `EKSRoleArn`: IAM role ARN for EKS pods (IRSA)
- `EC2RoleArn`: IAM role ARN for EC2 instances
- `EC2InstanceProfileArn`: IAM instance profile ARN for EC2
- `DashboardUrl`: CloudWatch dashboard URL

## Cost Optimization

1. **Lifecycle Policies:** Automatically clean up old images
2. **Regional Deployment:** Deploy in the same region as compute resources
3. **Image Optimization:** Use multi-stage builds and minimal base images
4. **Monitoring:** Use CloudWatch metrics to track usage and optimize retention

## Next Steps

1. Deploy the stack for your target environment
2. Configure EKS OIDC provider if using EKS
3. Set up GitHub Actions with the CI/CD role
4. Create Kubernetes ServiceAccount for IRSA
5. Test image pull/push operations
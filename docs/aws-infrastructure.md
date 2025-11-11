# AWS Infrastructure Deployment

The project includes CloudFormation templates and Sceptre configurations for deploying to AWS:

```bash
# Export infrastructure dependencies
pants export --resolve=infrastructure_env

# Navigate to infrastructure directory
cd epistemix_platform/infrastructure

# Validate CloudFormation templates
cfn-lint templates/**/*.json

# Deploy to staging environment
export DEVELOPER_IP="your.ip.address/32"
export AWS_REGION="us-east-1"
sceptre launch config/staging

# Update existing stack
sceptre update config/staging/epistemix-api-lambda.yaml

# Delete stack
sceptre delete config/staging/epistemix-api-lambda.yaml

# View stack outputs
sceptre list outputs config/staging
```

See [epistemix_platform/infrastructure/README.md](../epistemix_platform/infrastructure/README.md) for detailed infrastructure documentation.

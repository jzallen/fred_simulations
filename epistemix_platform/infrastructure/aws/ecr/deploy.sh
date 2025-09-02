#!/bin/bash

# ECR Repository Deployment Script
# Usage: ./deploy.sh <environment> [region]
# Example: ./deploy.sh dev us-east-1

set -e

ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    echo "Error: Environment must be dev, staging, or production"
    echo "Usage: $0 <environment> [region]"
    exit 1
fi

echo "Deploying ECR repository for environment: $ENVIRONMENT in region: $REGION"

# Check if Poetry is available
if ! command -v poetry &> /dev/null; then
    echo "Error: Poetry is not installed. Please install Poetry first."
    exit 1
fi

# Check if parameter file exists
PARAM_FILE="parameters-${ENVIRONMENT}.json"
if [[ ! -f "$PARAM_FILE" ]]; then
    echo "Error: Parameter file $PARAM_FILE not found"
    exit 1
fi

# Validate template
echo "Validating CloudFormation template..."
poetry run cfn-lint simulation-runner-repository.yaml

if [[ $? -ne 0 ]]; then
    echo "Error: Template validation failed"
    exit 1
fi

poetry run aws cloudformation validate-template \
    --template-body file://simulation-runner-repository.yaml \
    --region "$REGION"

if [[ $? -ne 0 ]]; then
    echo "Error: AWS template validation failed"
    exit 1
fi

echo "Template validation successful"

# Deploy stack
STACK_NAME="fred-ecr-repository-${ENVIRONMENT}"

echo "Deploying stack: $STACK_NAME"
echo "Using parameters: $PARAM_FILE"

poetry run aws cloudformation deploy \
    --template-file simulation-runner-repository.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides file://"$PARAM_FILE" \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION" \
    --no-fail-on-empty-changeset

if [[ $? -eq 0 ]]; then
    echo ""
    echo "Deployment successful!"
    echo ""
    echo "Getting stack outputs..."
    
    poetry run aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
else
    echo "Deployment failed"
    exit 1
fi
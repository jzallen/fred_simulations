#!/bin/bash
set -e

# Simulation runner entrypoint script
# Downloads job uploads and runs FRED simulation for a given job ID

echo "=== FRED Simulation Runner ==="

# Show help if no arguments provided
if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: run-simulation.sh <JOB_ID>"
    echo ""
    echo "Downloads all uploads for the specified job ID and runs FRED simulation."
    echo ""
    echo "Arguments:"
    echo "  JOB_ID    Required. The job ID to download uploads for and run simulation."
    echo ""
    echo "Environment Variables:"
    echo "  EPISTEMIX_API_URL       API endpoint URL (optional, defaults to config)"
    echo "  EPISTEMIX_S3_BUCKET     S3 bucket name (optional, defaults to config)"
    echo "  AWS_REGION              AWS region (optional, defaults to config)"
    echo "  DATABASE_URL            Database connection string (optional)"
    echo ""
    echo "Example:"
    echo "  run-simulation.sh 123"
    echo ""
    echo "Tip: Use epistemix-cli directly to list available jobs:"
    echo "  docker run --entrypoint epistemix-cli simulation-runner:latest jobs list"
    echo ""
    exit 0
fi

JOB_ID=$1

# Validate job ID is numeric
if ! [[ "$JOB_ID" =~ ^[0-9]+$ ]]; then
    echo "ERROR: JOB_ID must be a numeric value, got: $JOB_ID"
    exit 1
fi

echo "Job ID: $JOB_ID"

# Create job-specific workspace directory
WORKSPACE_DIR="/workspace/job_${JOB_ID}"
echo "Workspace: $WORKSPACE_DIR"

# Clean up workspace if it already exists (ensure fresh start)
if [ -d "$WORKSPACE_DIR" ]; then
    echo "Cleaning existing workspace..."
    rm -rf "$WORKSPACE_DIR"
fi

mkdir -p "$WORKSPACE_DIR"

# Show environment configuration (without exposing credentials)
if [ -n "$EPISTEMIX_API_URL" ]; then
    echo "API URL: $EPISTEMIX_API_URL"
else
    echo "API URL: Using default from ~/.epistemix/cli.env"
fi

if [ -n "$EPISTEMIX_S3_BUCKET" ]; then
    echo "S3 Bucket: $EPISTEMIX_S3_BUCKET"
fi

if [ -n "$AWS_REGION" ]; then
    echo "AWS Region: $AWS_REGION"
fi

# Download job uploads using epistemix-cli
echo ""
echo "Downloading uploads for job $JOB_ID..."
if epistemix-cli jobs uploads download --job-id "$JOB_ID" --output-dir "$WORKSPACE_DIR" -f; then
    echo "Successfully downloaded uploads"
else
    echo "ERROR: Failed to download uploads for job $JOB_ID"
    echo "Check that:"
    echo "  1. Job ID $JOB_ID exists in the database"
    echo "  2. Job has uploads associated with it"
    echo "  3. API endpoint is accessible"
    echo "  4. AWS credentials are configured (for S3 access)"
    exit 1
fi

# Verify files were downloaded
DOWNLOADED_FILES=$(find "$WORKSPACE_DIR" -type f | wc -l)
if [ "$DOWNLOADED_FILES" -eq 0 ]; then
    echo "ERROR: No files were downloaded for job $JOB_ID"
    echo "Job may not have any uploads."
    exit 1
fi

echo "Downloaded $DOWNLOADED_FILES file(s)"
echo ""
echo "Files in workspace:"
ls -lh "$WORKSPACE_DIR"

# TODO: Run FRED simulation with downloaded files
# This will be implemented in a future iteration when we add the 'jobs run' command
echo ""
echo "=== Ready to run FRED simulation ==="
echo "Workspace prepared at: $WORKSPACE_DIR"
echo ""
echo "Note: FRED simulation execution will be added in a future update."
echo "For now, files are downloaded and ready for processing."

# Exit successfully
exit 0

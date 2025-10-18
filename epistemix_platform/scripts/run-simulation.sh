#!/bin/bash
set -e

# Simulation runner entrypoint script
# Downloads job uploads and runs FRED simulation for a given job ID

echo "=== FRED Simulation Runner ==="

# Show help if no arguments provided
if [ $# -eq 0 ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: run-simulation.sh <JOB_ID> [RUN_ID]"
    echo ""
    echo "Downloads uploads for the specified job and run, then validates FRED configuration."
    echo ""
    echo "Arguments:"
    echo "  JOB_ID    Required. The job ID to download uploads for."
    echo "  RUN_ID    Optional. Specific run ID to process. If not specified, processes all runs."
    echo ""
    echo "Environment Variables:"
    echo "  EPISTEMIX_API_URL       API endpoint URL (optional, defaults to config)"
    echo "  EPISTEMIX_S3_BUCKET     S3 bucket name (optional, defaults to config)"
    echo "  AWS_REGION              AWS region (optional, defaults to config)"
    echo "  DATABASE_URL            Database connection string (optional)"
    echo ""
    echo "Examples:"
    echo "  run-simulation.sh 12           # Process all runs for job 12"
    echo "  run-simulation.sh 12 4         # Process only run 4 of job 12"
    echo ""
    echo "Tip: Use epistemix-cli directly to list available jobs:"
    echo "  docker run --entrypoint epistemix-cli simulation-runner:latest jobs list"
    echo ""
    exit 0
fi

JOB_ID=$1
RUN_ID=$2

# Validate job ID is numeric
if ! [[ "$JOB_ID" =~ ^[0-9]+$ ]]; then
    echo "ERROR: JOB_ID must be a numeric value, got: $JOB_ID"
    exit 1
fi

# Validate run ID if provided
if [ -n "$RUN_ID" ]; then
    if ! [[ "$RUN_ID" =~ ^[0-9]+$ ]]; then
        echo "ERROR: RUN_ID must be a numeric value, got: $RUN_ID"
        exit 1
    fi
    echo "Job ID: $JOB_ID, Run ID: $RUN_ID"
else
    echo "Job ID: $JOB_ID (processing all runs)"
fi

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

# Extract and prepare FRED configuration
echo ""
echo "=== Preparing FRED Configuration ==="

# Extract job_input.zip if it exists
if [ -f "$WORKSPACE_DIR/job_input.zip" ]; then
    echo "Extracting job_input.zip..."
    python3 -m zipfile -e "$WORKSPACE_DIR/job_input.zip" "$WORKSPACE_DIR"
    echo "✓ Extracted job_input.zip"
fi

# Find run config file(s)
if [ -n "$RUN_ID" ]; then
    # Specific run ID requested
    RUN_CONFIG="$WORKSPACE_DIR/run_${RUN_ID}_config.json"
    if [ ! -f "$RUN_CONFIG" ]; then
        echo "ERROR: Run config not found: $RUN_CONFIG"
        echo "Available run configs:"
        find "$WORKSPACE_DIR" -name "run_*_config.json" -exec basename {} \; || echo "  (none found)"
        exit 1
    fi
    RUN_CONFIGS="$RUN_CONFIG"
else
    # Process all runs
    RUN_CONFIGS=$(find "$WORKSPACE_DIR" -name "run_*_config.json" | sort)
fi

if [ -z "$RUN_CONFIGS" ]; then
    echo "WARNING: No run config files found (run_*_config.json)"
    echo "Skipping FRED configuration preparation"
else
    # Process each run config
    for RUN_CONFIG in $RUN_CONFIGS; do
        CURRENT_RUN_ID=$(basename "$RUN_CONFIG" | sed -n 's/run_\([0-9]*\)_config.json/\1/p')
        echo ""
        echo "Processing run $CURRENT_RUN_ID..."

        # Check if main.fred exists
        if [ ! -f "$WORKSPACE_DIR/main.fred" ]; then
            echo "WARNING: main.fred not found, skipping FRED preparation for run $CURRENT_RUN_ID"
            continue
        fi

        # Prepare FRED configuration
        PREPARED_FRED="$WORKSPACE_DIR/run_${CURRENT_RUN_ID}_prepared.fred"
        echo "Preparing FRED config: $PREPARED_FRED"

        if python3 /usr/local/bin/prepare_fred_config.py \
            "$RUN_CONFIG" \
            "$WORKSPACE_DIR/main.fred" \
            "$PREPARED_FRED" \
            --verbose; then
            echo "✓ Successfully prepared FRED configuration"

            # Validate with FRED check flag
            echo ""
            echo "Validating FRED configuration..."
            VALIDATION_LOG="$WORKSPACE_DIR/run_${CURRENT_RUN_ID}_validation.log"

            export FRED_HOME=/fred-framework
            if /usr/local/bin/FRED -p "$PREPARED_FRED" -c > "$VALIDATION_LOG" 2>&1; then
                echo "✓ FRED validation passed"
                echo "Validation log saved to: $VALIDATION_LOG"

                # Extract run number from prepare_fred_config.py output
                # The seed is converted to a 16-bit run number
                RUN_NUMBER=$(grep "FRED -p.*-r" "$VALIDATION_LOG" | sed -n 's/.*-r \([0-9]*\).*/\1/p' || echo "1")
                if [ -z "$RUN_NUMBER" ]; then
                    # Fallback: calculate run number from seed
                    SEED=$(grep "seed" "$RUN_CONFIG" | grep -o '[0-9]*' | head -1)
                    if [ -n "$SEED" ]; then
                        # Simple modulo to fit in 16-bit range
                        RUN_NUMBER=$((SEED % 65536 + 1))
                    else
                        RUN_NUMBER=1
                    fi
                fi

                # Run FRED simulation
                echo ""
                echo "=== Running FRED Simulation ==="
                echo "Run number: $RUN_NUMBER"

                OUTPUT_DIR="$WORKSPACE_DIR/OUT/run_${CURRENT_RUN_ID}"
                mkdir -p "$OUTPUT_DIR"

                SIMULATION_LOG="$WORKSPACE_DIR/run_${CURRENT_RUN_ID}_simulation.log"

                echo "Output directory: $OUTPUT_DIR"
                echo "Starting FRED simulation..."

                if /usr/local/bin/FRED -p "$PREPARED_FRED" -r "$RUN_NUMBER" -d "$OUTPUT_DIR" > "$SIMULATION_LOG" 2>&1; then
                    echo "✓ FRED simulation completed successfully"
                    echo "Simulation log saved to: $SIMULATION_LOG"
                    echo ""
                    echo "Output files:"
                    ls -lh "$OUTPUT_DIR" | head -20
                else
                    echo "✗ FRED simulation failed (see log for details)"
                    echo "Simulation log saved to: $SIMULATION_LOG"
                    echo ""
                    echo "Last 30 lines of simulation log:"
                    tail -30 "$SIMULATION_LOG"
                fi
            else
                echo "✗ FRED validation failed (see log for details)"
                echo "Validation log saved to: $VALIDATION_LOG"
                echo ""
                echo "Last 20 lines of validation log:"
                tail -20 "$VALIDATION_LOG"
                echo ""
                echo "Skipping simulation run due to validation failure"
            fi
        else
            echo "✗ Failed to prepare FRED configuration for run $CURRENT_RUN_ID"
        fi
    done
fi

# Final summary
echo ""
echo "=== Simulation Complete ==="
echo "Workspace: $WORKSPACE_DIR"
echo ""

# Count simulation outputs
OUTPUT_COUNT=$(find "$WORKSPACE_DIR/OUT" -type f 2>/dev/null | wc -l)
if [ "$OUTPUT_COUNT" -gt 0 ]; then
    echo "Simulation outputs: $OUTPUT_COUNT files in $WORKSPACE_DIR/OUT/"
    echo ""
    echo "Output directory structure:"
    ls -lh "$WORKSPACE_DIR/OUT/" 2>/dev/null || echo "  (no output directory)"
else
    echo "No simulation outputs generated (validation may have failed)"
fi

echo ""
echo "Configuration files:"
ls -lh "$WORKSPACE_DIR"/*.{fred,json} 2>/dev/null | head -10 || echo "  (none found)"

echo ""
echo "Log files:"
ls -lh "$WORKSPACE_DIR"/*.log 2>/dev/null || echo "  (none found)"

# Exit successfully
exit 0

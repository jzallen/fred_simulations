#!/bin/bash

# FRED Simulation Script
# This script replaces main.cpp and uses FRED's CLI interface

echo "Starting FRED Simulation via CLI..."

# Check if FRED_HOME is set (should be set by devcontainer)
if [ -z "$FRED_HOME" ]; then
    echo "FRED_HOME not set, setting default..."
    export FRED_HOME="/workspaces/fred_simulations/fred-framework"
    export PATH="$FRED_HOME/bin:$PATH"
else
    echo "Using FRED_HOME: $FRED_HOME"
fi

# Create output directory
OUTPUT_DIR="output"
mkdir -p "$OUTPUT_DIR"

# Create a simple simulation configuration
CONFIG_FILE="simulation_config.fred"
cat > "$CONFIG_FILE" << EOF
# Basic FRED Simulation Configuration using available test data
locations = 42003
days = 10
quality_control = 0
verbose = 1
enable_health_records = 1
enable_var_records = 1

# Output settings
output_directory = $OUTPUT_DIR
start_date = 2025-01-01

# Basic disease model (influenza-like)
condition Influenza {
    transmissibility = 0.5
    symptomatic_fraction = 0.67
    incubation_days = uniform(1, 3)
    infectious_days = uniform(3, 7)
    recovery_days = uniform(5, 10)
}
EOF

echo "Created configuration file: $CONFIG_FILE"

# Run the FRED simulation
echo "Running FRED simulation for 10 days..."
RUN_NUMBER=1

# Execute FRED with our configuration
"$FRED_HOME/bin/FRED" -p "$CONFIG_FILE" -r "$RUN_NUMBER" -d "$OUTPUT_DIR"

# Check if simulation completed successfully
if [ $? -eq 0 ]; then
    echo "FRED simulation completed successfully!"
    
    # Display some basic results if available
    if [ -d "$OUTPUT_DIR" ]; then
        echo "Output directory contents:"
        ls -la "$OUTPUT_DIR/"
        
        # Try to show some basic statistics if files exist
        if [ -f "$OUTPUT_DIR/out1.txt" ]; then
            echo "Sample output from simulation:"
            head -10 "$OUTPUT_DIR/out1.txt"
        fi
    fi
else
    echo "FRED simulation failed with exit code $?"
    echo "Check the configuration and try again."
fi

echo "FRED Simulation Script Completed."

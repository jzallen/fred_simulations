#!/bin/bash

# Extended FRED CLI Demonstration Script
# This script shows various FRED CLI utilities and commands

echo "=== FRED CLI Utilities Demo ==="

# Set up FRED environment
export FRED_HOME="/workspaces/fred_simulations/fred-framework"
export PATH="$FRED_HOME/bin:$PATH"

echo "FRED Home: $FRED_HOME"
echo "FRED Version:"
fred_version 2>/dev/null || echo "Version command not available"

echo ""
echo "=== Available FRED CLI Commands ==="
echo "Main simulation commands:"
echo "  FRED               - Main simulation executable"
echo "  fred_run           - Run FRED simulation"
echo "  fred_job           - Manage simulation jobs"
echo ""
echo "Analysis and visualization:"
echo "  fred_plot          - Create plots from simulation data"
echo "  fred_map           - Create maps from simulation data"
echo "  fred_stats         - Generate statistics"
echo "  fred_csv           - Convert output to CSV format"
echo ""
echo "Utility commands:"
echo "  fred_status        - Check simulation status"
echo "  fred_get_counts    - Get population counts"
echo "  fred_popsize       - Get population size"
echo ""

echo "=== Running Basic Population Query ==="
# Try to get population information for our test location
echo "Population info for location 42003:"
fred_popsize -l 42003 2>/dev/null || echo "Population query failed - data may not be available"

echo ""
echo "=== Available FRED Configuration Example ==="
echo "Here's a minimal working FRED configuration:"
cat << 'EOF'
# minimal_fred.config
locations = 42003
days = 5
verbose = 1
enable_health_records = 1

condition Influenza {
    transmissibility = 0.3
    symptomatic_fraction = 0.6
    incubation_days = uniform(1, 3)
    infectious_days = uniform(3, 7)
}
EOF

echo ""
echo "=== To run a simulation manually ==="
echo "1. Create a configuration file like the one above"
echo "2. Run: FRED -p your_config.fred -r 1 -d output_directory"
echo "3. Check results in the output directory"

echo ""
echo "=== FRED CLI Demo Complete ==="

#!/bin/bash

# Script to run the Epistemix API Flask server

set -e

echo "Starting Epistemix API Mock Server..."

# Set default environment variables
export FLASK_HOST=${FLASK_HOST:-"0.0.0.0"}
export FLASK_PORT=${FLASK_PORT:-5000}
export FLASK_ENV=${FLASK_ENV:-"development"}
export FLASK_DEBUG=${FLASK_DEBUG:-"True"}

# Change to the epistemix_platform directory
cd "$(dirname "$0")/epistemix_platform"

# Run the server using Poetry if available, otherwise use Python directly
if command -v poetry &> /dev/null; then
    echo "Using Poetry to run the server..."
    cd ..
    poetry run python epistemix_platform/run_server.py
else
    echo "Poetry not found, using Python directly..."
    python run_server.py
fi

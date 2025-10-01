#!/bin/bash
set -e

# Migration runner entrypoint script
# Can be used for local development or as a bastion for production RDS migrations

echo "=== Epistemix Database Migration Runner ==="

# Default to local development database if DATABASE_URL not set
if [ -z "$DATABASE_URL" ]; then
    echo "No DATABASE_URL provided, using local development database"
    export DATABASE_URL="postgresql://epistemix_user:epistemix_password@postgres:5432/epistemix_db"
fi

# Handle postgres:// -> postgresql:// conversion for compatibility
if [[ "$DATABASE_URL" == postgres://* ]]; then
    export DATABASE_URL="${DATABASE_URL/postgres:/postgresql:}"
fi

echo "Database URL: ${DATABASE_URL%%@*}@***" # Hide credentials in output

# Wait for database to be available (with timeout)
echo "Waiting for database to be available..."

# Parse DATABASE_URL for connection details
# Format: postgresql://user:password@host:port/database
DB_URL="$DATABASE_URL"
DB_USER=$(echo $DB_URL | sed -n 's#.*://\([^:]*\):.*#\1#p')
DB_PASS=$(echo $DB_URL | sed -n 's#.*://[^:]*:\([^@]*\)@.*#\1#p')
DB_HOST=$(echo $DB_URL | sed -n 's#.*@\([^:]*\):.*#\1#p')
DB_PORT=$(echo $DB_URL | sed -n 's#.*:\([0-9]*\)/.*#\1#p')
DB_NAME=$(echo $DB_URL | sed -n 's#.*/\([^?]*\).*#\1#p')

timeout=30
counter=0
until PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null || [ $counter -eq $timeout ]; do
    echo "Waiting for database... ($counter/$timeout)"
    sleep 1
    counter=$((counter+1))
done

if [ $counter -eq $timeout ]; then
    echo "ERROR: Database connection timeout after ${timeout} seconds"
    echo "Connection details: host=$DB_HOST port=$DB_PORT user=$DB_USER database=$DB_NAME"
    exit 1
fi

echo "Database is available!"

# Change to the epistemix_platform directory
cd /fred_simulations/epistemix_platform

# Set PYTHONPATH to include the src directory
export PYTHONPATH="/fred_simulations/epistemix_platform/src:/fred_simulations/epistemix_platform:$PYTHONPATH"

# Run the command passed to the container, or default to showing migration status
if [ $# -eq 0 ]; then
    echo "Showing current migration status..."
    alembic current
else
    echo "Running command: $@"
    exec "$@"
fi
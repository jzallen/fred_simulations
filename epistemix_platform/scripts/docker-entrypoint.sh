#!/bin/bash
set -e

echo "Starting Epistemix API server..."
echo "Environment: ${FLASK_ENV:-production}"
echo "Port: 5555"

# Function to handle shutdown gracefully
shutdown() {
    echo "Shutting down services..."
    if [ ! -z "$NGINX_PID" ]; then
        kill -TERM "$NGINX_PID" 2>/dev/null || true
    fi
    if [ ! -z "$GUNICORN_PID" ]; then
        kill -TERM "$GUNICORN_PID" 2>/dev/null || true
    fi
    exit 0
}

# Set up signal handlers
trap shutdown SIGTERM SIGINT

# Start nginx in background
echo "Starting nginx..."
nginx -c /etc/nginx/nginx.conf &
NGINX_PID=$!

# Give nginx a moment to start
sleep 1

# Check if nginx started successfully
if ! kill -0 $NGINX_PID 2>/dev/null; then
    echo "Error: nginx failed to start"
    exit 1
fi

echo "nginx started successfully (PID: $NGINX_PID)"

# Start Gunicorn in background using PEX
echo "Starting Gunicorn..."
PEX_MODULE=gunicorn /app/app.pex epistemix_platform.wsgi:application \
    --config /app/configs/gunicorn.conf.py \
    &
GUNICORN_PID=$!

# Wait for either process to exit
wait -n $NGINX_PID $GUNICORN_PID

# If we get here, one of the processes has died
echo "Error: One of the services has stopped unexpectedly"
shutdown
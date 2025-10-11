"""Gunicorn configuration for production deployment."""

import os

# Server socket - bind to TCP port for Lambda Web Adapter or traditional deployment
# Lambda Web Adapter expects PORT environment variable
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"

# Worker processes - Lambda handles concurrency, so we use minimal workers in Lambda
# For traditional deployment, this can be overridden via environment variable
workers = int(os.environ.get('GUNICORN_WORKERS', '1'))
worker_class = "sync"  # Simple synchronous workers work well for Lambda
threads = 1  # Single thread per worker for Lambda

# Timeout settings
timeout = 120
keepalive = 2
graceful_timeout = 30

# Request handling
max_requests = 1000
max_requests_jitter = 50

# Application preloading
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "epistemix-api"

# StatsD (optional, for monitoring)
# statsd_host = "localhost:8125"
# statsd_prefix = "epistemix_api"
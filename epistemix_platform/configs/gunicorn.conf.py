"""Gunicorn configuration for production deployment."""

# Server socket
bind = "unix:/tmp/gunicorn.sock"

# Worker processes
workers = 4
worker_class = "gthread"  # Use gthread instead of gevent to avoid SSL monkey patching issues
worker_connections = 1000
threads = 4  # Number of threads per worker

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
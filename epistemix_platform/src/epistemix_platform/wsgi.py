"""
WSGI entry point for production deployment.

This module provides the WSGI application object that Gunicorn will use
to serve the Epistemix API in production environments.
"""

import os
import sys
import logging
from urllib.parse import urlsplit, urlunsplit

from epistemix_platform.app import app
from epistemix_platform.config import config

# Configure logging for production with level-based stream separation
class _MaxLevelFilter(logging.Filter):
    """Filter to limit handler to messages below a certain level."""
    def __init__(self, level):
        super().__init__()
        self.level = level
    def filter(self, record):
        return record.levelno < self.level

# Reset root logger and attach filtered handlers
root = logging.getLogger()
for h in list(root.handlers):
    root.removeHandler(h)
root.setLevel(logging.INFO)

# Create formatter for consistent log format
fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# stdout handler for INFO, WARNING (but not ERROR)
stdout_h = logging.StreamHandler(sys.stdout)
stdout_h.setLevel(logging.INFO)
stdout_h.addFilter(_MaxLevelFilter(logging.ERROR))
stdout_h.setFormatter(fmt)

# stderr handler for ERROR and CRITICAL only
stderr_h = logging.StreamHandler(sys.stderr)
stderr_h.setLevel(logging.ERROR)
stderr_h.setFormatter(fmt)

root.addHandler(stdout_h)
root.addHandler(stderr_h)

logger = logging.getLogger(__name__)

# Also configure Flask's logger to use the same handlers
app.logger.handlers = root.handlers
app.logger.setLevel(logging.INFO)

# Get configuration from environment
config_name = os.getenv("FLASK_ENV", "production")
logger.info(f"Loading configuration for environment: {config_name}")

# Apply configuration to Flask app
app.config.from_object(config.get(config_name, config["default"]))

# Additional production configurations
app.config['PROPAGATE_EXCEPTIONS'] = True

# Log startup information
logger.info(f"Epistemix API WSGI application initialized for {config_name} environment")

# WSGI application object - this is what Gunicorn will import
application = app

# Optional: Add middleware for production (e.g., ProxyFix for reverse proxy)
from werkzeug.middleware.proxy_fix import ProxyFix
application = ProxyFix(application, x_for=1, x_proto=1, x_host=1, x_prefix=1)
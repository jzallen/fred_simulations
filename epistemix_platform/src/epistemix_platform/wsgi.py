"""
WSGI entry point for production deployment.

This module provides the WSGI application object that Gunicorn will use
to serve the Epistemix API in production environments.
"""

import os
import sys
import logging

from epistemix_platform.app import app
from epistemix_platform.config import config

# Configure logging for production - ensure output to stdout/stderr
logging.basicConfig(
    level=logging.INFO,  # This includes ERROR, WARNING, and INFO levels
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Explicitly use stdout for normal logs
        logging.StreamHandler(sys.stderr)   # Use stderr for errors
    ],
    force=True  # Force reconfiguration of the root logger
)
logger = logging.getLogger(__name__)

# Also configure Flask's logger to use the same handlers
app.logger.handlers = logging.getLogger().handlers
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
logger.info(f"Database URL: {app.config.get('DATABASE_URL', 'Not configured')}")

# WSGI application object - this is what Gunicorn will import
application = app

# Optional: Add middleware for production (e.g., ProxyFix for reverse proxy)
from werkzeug.middleware.proxy_fix import ProxyFix
application = ProxyFix(application, x_for=1, x_proto=1, x_host=1, x_prefix=1)
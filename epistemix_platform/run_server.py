#!/usr/bin/env python3
"""
Script to run the Epistemix API Flask app for LOCAL DEVELOPMENT.

Note: This script uses Flask's built-in development server and is intended
for local development and testing only. For production deployment, use the
Docker container which includes Gunicorn and nginx for proper WSGI serving.

To build and run the production Docker container:
  pants package //:epistemix-api
  docker run -p 5555:5555 epistemix-api:latest
"""

import os

from epistemix_platform.app import app
from epistemix_platform.config import config


def main():
    """Main function to run the Flask app."""
    # Get configuration from environment
    config_name = os.getenv("FLASK_ENV", "development")
    app.config.from_object(config.get(config_name, config["default"]))

    # Get runtime settings
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    print("Starting Epistemix API Mock Server...")
    print(f"Environment: {config_name}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Access the API at: http://{host}:{port}")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()

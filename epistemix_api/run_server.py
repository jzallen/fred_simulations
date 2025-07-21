#!/usr/bin/env python3
"""
Script to run the Epistemix API Flask app.
"""

import os
import sys
from pathlib import Path

# Add the epistemix_api directory to the Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app import app
from config import config

def main():
    """Main function to run the Flask app."""
    # Get configuration from environment
    config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config.get(config_name, config['default']))
    
    # Get runtime settings
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"Starting Epistemix API Mock Server...")
    print(f"Environment: {config_name}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Access the API at: http://{host}:{port}")
    
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()

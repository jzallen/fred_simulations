"""
Configuration settings for the Epistemix API Flask app.
"""

import os
from typing import Any, Dict


class Config:
    """Base configuration class."""

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # API settings
    API_VERSION = "1.0.0"
    API_TITLE = "Epistemix API Mock"

    # CORS settings
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    @staticmethod
    def init_app(app):
        """Initialize app with this configuration."""
        pass


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    TESTING = False
    S3_UPLOAD_BUCKET = os.environ.get("S3_UPLOAD_BUCKET", "epistemix-uploads-dev")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    WTF_CSRF_ENABLED = False


class TestingConfig(Config):
    """Testing configuration."""

    DEBUG = False
    TESTING = True
    S3_UPLOAD_BUCKET = os.environ.get("S3_UPLOAD_BUCKET", "epistemix-uploads-test")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    TESTING = False
    S3_UPLOAD_BUCKET = os.environ.get("S3_UPLOAD_BUCKET", "epistemix-uploads-prod")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
    WTF_CSRF_ENABLED = True


# Configuration mapping
config: Dict[str, Any] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

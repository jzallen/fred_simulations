"""
Utils package for the Epistemix platform.

This package contains application utilities that encapsulate business logic
and coordinate between domain models and infrastructure.
"""

from epistemix_platform.utils.s3_client import create_s3_client


__all__ = [
    # S3 Client
    "create_s3_client",
]

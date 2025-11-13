"""
S3 client creation utility for AWS S3 operations.

This module provides a centralized function for creating boto3 S3 clients
with proper error handling and credential chain support.
"""

import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, NoCredentialsError


logger = logging.getLogger(__name__)


def create_s3_client(region_name: str | None = None, s3_client: Any | None = None) -> Any:
    """
    Create or validate an S3 client with proper error handling.

    This function centralizes S3 client creation logic, supporting both:
    1. Injection of a pre-configured client (for testing)
    2. Creation of a new client using AWS default credential chain

    AWS Default Credential Chain (when s3_client=None):
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    2. AWS credentials file (~/.aws/credentials)
    3. AWS config file (~/.aws/config)
    4. IAM roles for EC2 instances
    5. IAM roles for containers (ECS, EKS)
    6. AWS SSO

    Args:
        region_name: AWS region name (optional, will use default region from config/environment)
        s3_client: Optional pre-configured S3 client (for testing)

    Returns:
        Configured boto3 S3 client

    Raises:
        ValueError: If S3 client initialization fails due to missing credentials or other errors
    """

    # Use injected client when provided (testing/DI)
    if s3_client is not None:
        try:
            actual_region = (
                getattr(getattr(s3_client, "meta", None), "region_name", None) or "default"
            )
            logger.info(f"Using injected S3 client (region: {actual_region})")
        except Exception:
            logger.info("Using injected S3 client")
        return s3_client

    # Initialize S3 client using default credential chain
    session_kwargs: dict[str, Any] = {}
    if region_name:
        session_kwargs["region_name"] = region_name
    try:
        client = boto3.client("s3", **session_kwargs)
    except (NoCredentialsError, BotoCoreError) as e:
        logger.exception("Failed to initialize S3 client")
        raise ValueError("S3 client initialization failed") from e
    actual_region = getattr(getattr(client, "meta", None), "region_name", None) or "default"
    logger.info(f"S3 client initialized for region: {actual_region}")
    return client

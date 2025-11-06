"""Bootstrap configuration module for loading config from multiple sources.

This module provides functions to load configuration from:
1. .env files (using python-dotenv)
2. AWS Parameter Store (using boto3)
3. Environment variables (highest priority)

Priority order:
- .env file values are loaded first
- Environment variables override .env values
- AWS Parameter Store fills in missing values

This module has zero dependencies on Flask or application code and can be
used from any application (epistemix_platform, simulation_runner, etc.).
"""

import os
from urllib.parse import quote_plus

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def load_dotenv_if_exists(dotenv_path: str = ".env") -> None:
    """Load environment variables from .env file if it exists.

    Uses python-dotenv to parse and load the .env file. If the file doesn't
    exist, the function continues silently without raising an error.

    Existing environment variables take precedence over values in the .env file
    (python-dotenv default behavior with override=False).

    Args:
        dotenv_path: Path to the .env file. Defaults to ".env" in current directory.

    Example:
        >>> load_dotenv_if_exists()  # Load from .env
        >>> load_dotenv_if_exists("/path/to/.env")  # Load from specific path
    """
    # load_dotenv returns False if file doesn't exist, but doesn't raise exception
    # override=False means existing env vars are NOT overridden by .env values
    load_dotenv(dotenv_path=dotenv_path, override=False)


def load_from_parameter_store(environment: str = "dev") -> None:
    """Load configuration from AWS Parameter Store into os.environ.

    Fetches all parameters under the path `/epistemix/{environment}/` and maps
    them to environment variables. For example:
    - `/epistemix/dev/database/host` → `DATABASE_HOST`
    - `/epistemix/dev/database/user` → `DATABASE_USER`

    Note: Database password is NOT loaded from Parameter Store. It's stored
    in AWS Secrets Manager for better security. Use load_from_secrets_manager()
    to fetch the password.

    Only sets environment variables if they are NOT already set, respecting
    existing values from .env files or explicit environment settings.

    Handles AWS errors gracefully:
    - No credentials configured: continues silently
    - AccessDenied errors: continues silently
    - Network errors: continues silently
    - Other errors: continues silently

    Args:
        environment: The environment name (dev, staging, production, etc.).
                    Used as part of Parameter Store path. Defaults to "dev".

    Example:
        >>> load_from_parameter_store("production")
        >>> load_from_parameter_store()  # Uses "dev" by default
    """
    try:
        # Create SSM client
        ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", "us-east-1"))

        # Fetch all parameters under the environment path
        path = f"/epistemix/{environment}/"

        # Get parameters recursively with decryption enabled for SecureString
        paginator = ssm.get_paginator("get_parameters_by_path")
        page_iterator = paginator.paginate(
            Path=path,
            Recursive=True,
            WithDecryption=True,  # Decrypt SecureString parameters
        )

        # Process all parameters
        for page in page_iterator:
            for parameter in page.get("Parameters", []):
                # Extract parameter name and value
                param_name = parameter["Name"]
                param_value = parameter["Value"]

                # Map parameter path to environment variable name
                # /epistemix/dev/database/host → DATABASE_HOST
                # Remove the prefix /epistemix/{environment}/
                env_var_name = param_name.replace(path, "").replace("/", "_").upper()

                # Only set if not already set (respects .env and existing env vars)
                if env_var_name not in os.environ:
                    os.environ[env_var_name] = param_value

    except ClientError:
        # Handle AWS errors gracefully
        # Common cases:
        # - NoCredentialsError: local dev without AWS credentials
        # - AccessDeniedException: insufficient permissions
        # - ParameterNotFound: no parameters exist for this environment
        # All cases: continue silently to allow local development
        pass
    except Exception:
        # Catch-all for network errors, connection timeouts, etc.
        # Continue silently - local development should not require AWS
        pass


def load_from_secrets_manager(environment: str = "dev") -> None:
    """Load sensitive configuration from AWS Secrets Manager into os.environ.

    Fetches database password from Secrets Manager at path:
    `/epistemix/{environment}/database/password`

    This is separate from Parameter Store because:
    - Secrets Manager provides better encryption and rotation for credentials
    - CloudFormation doesn't support SecureString for SSM parameters
    - AWS best practice: use Secrets Manager for database passwords

    Only sets environment variables if they are NOT already set, respecting
    existing values from .env files or explicit environment settings.

    Handles AWS errors gracefully:
    - No credentials configured: continues silently
    - AccessDenied errors: continues silently
    - Network errors: continues silently
    - Other errors: continues silently

    Args:
        environment: The environment name (dev, staging, production, etc.).
                    Used as part of secret name. Defaults to "dev".

    Example:
        >>> load_from_secrets_manager("production")
        >>> load_from_secrets_manager()  # Uses "dev" by default
    """
    try:
        # Create Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))

        # Fetch database password secret
        secret_name = f"/epistemix/{environment}/database/password"

        # Only fetch if DATABASE_PASSWORD not already set
        if "DATABASE_PASSWORD" not in os.environ:
            response = secrets_client.get_secret_value(SecretId=secret_name)
            # SecretString contains the plaintext password
            os.environ["DATABASE_PASSWORD"] = response["SecretString"]

    except ClientError:
        # Handle AWS errors gracefully
        # Common cases:
        # - NoCredentialsError: local dev without AWS credentials
        # - AccessDeniedException: insufficient permissions
        # - ResourceNotFoundException: secret doesn't exist for this environment
        # All cases: continue silently to allow local development
        pass
    except Exception:
        # Catch-all for network errors, connection timeouts, etc.
        # Continue silently - local development should not require AWS
        pass


def _build_database_url_if_needed() -> None:
    """Build DATABASE_URL from individual components if not already set.

    Constructs PostgreSQL connection URL from environment variables:
    - DATABASE_USER
    - DATABASE_PASSWORD
    - DATABASE_HOST
    - DATABASE_PORT
    - DATABASE_NAME

    Only builds URL if:
    1. DATABASE_URL is not already set
    2. All required components are available

    Sets DATABASE_URL in format: postgresql://{user}:{password}@{host}:{port}/{name}

    Security:
        - URL-encodes username and password to handle special characters (@, :, #, %, etc.)
        - Prevents connection failures when credentials contain reserved URL characters
    """
    # Only build if DATABASE_URL not already set
    if "DATABASE_URL" in os.environ:
        return

    # Check if all required components are available
    required = [
        "DATABASE_USER",
        "DATABASE_PASSWORD",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "DATABASE_NAME",
    ]  # noqa: E501
    if not all(key in os.environ for key in required):
        return

    # Build PostgreSQL URL with URL-encoded credentials
    # quote_plus encodes special chars: @ -> %40, : -> %3A, # -> %23, etc.
    user = quote_plus(os.environ["DATABASE_USER"])
    password = quote_plus(os.environ["DATABASE_PASSWORD"])
    host = os.environ["DATABASE_HOST"]
    port = os.environ["DATABASE_PORT"]
    name = os.environ["DATABASE_NAME"]

    database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    os.environ["DATABASE_URL"] = database_url


def bootstrap_config(environment: str | None = None) -> None:
    """Bootstrap configuration from .env file and environment variables.

    Main entry point for loading configuration. Priority order:
    1. Load from .env file (if exists) - lowest priority
    2. Existing environment variables override .env values

    In production (Lambda, ECS, etc.):
        - CloudFormation/Sceptre resolves Parameter Store and Secrets Manager values
        - These are injected as environment variables at deployment time
        - No runtime AWS API calls needed

    In local development:
        - .env file contains all required configuration
        - No AWS credentials or API calls required

    Args:
        environment: Optional environment name (currently unused, kept for compatibility).

    Example:
        >>> bootstrap_config()  # Load .env if exists, respect existing env vars
    """
    # Load .env file for local development
    # Existing environment variables take precedence (override=False)
    load_dotenv_if_exists()

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
    - `/epistemix/dev/database/password` → `DATABASE_PASSWORD`

    Only sets environment variables if they are NOT already set, respecting
    existing values from .env files or explicit environment settings.

    If all database components are loaded and DATABASE_URL is not set, constructs
    DATABASE_URL in PostgreSQL format:
    `postgresql://{user}:{password}@{host}:{port}/{name}`

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

        # Build DATABASE_URL from components if not already set
        _build_database_url_if_needed()

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

    # Build PostgreSQL URL
    user = os.environ["DATABASE_USER"]
    password = os.environ["DATABASE_PASSWORD"]
    host = os.environ["DATABASE_HOST"]
    port = os.environ["DATABASE_PORT"]
    name = os.environ["DATABASE_NAME"]

    database_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    os.environ["DATABASE_URL"] = database_url


def bootstrap_config(environment: str | None = None) -> None:
    """Bootstrap configuration from all sources with proper priority.

    Main entry point for loading configuration. Calls functions in priority order:
    1. Load from .env file (if exists)
    2. Existing environment variables (not modified)
    3. Load from AWS Parameter Store (fills in missing values)

    The environment parameter or ENVIRONMENT variable determines which Parameter
    Store path to use. Defaults to "dev" if neither is specified.

    Args:
        environment: Optional environment name. If not provided, uses the
                    ENVIRONMENT environment variable, or defaults to "dev".

    Example:
        >>> bootstrap_config()  # Use ENVIRONMENT var or default to "dev"
        >>> bootstrap_config("production")  # Explicit environment
    """
    # Load .env file first (lowest priority, but loaded first)
    load_dotenv_if_exists()

    # Determine environment
    # Priority: explicit argument > ENVIRONMENT env var > "dev" default
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "dev")

    # Load from AWS Parameter Store (only sets missing values)
    load_from_parameter_store(environment)

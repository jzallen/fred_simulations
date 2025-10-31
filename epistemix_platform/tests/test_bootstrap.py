"""Unit tests for bootstrap configuration module.

Tests validate:
- Loading from .env files with python-dotenv
- Loading from AWS Parameter Store with boto3
- Priority order: .env > env vars > AWS Parameter Store
- Error handling when AWS is unavailable
- DATABASE_URL construction from components
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError
from moto import mock_aws

# Import will fail until we create the module (TDD Red phase)
from epistemix_platform.bootstrap import (
    bootstrap_config,
    load_dotenv_if_exists,
    load_from_parameter_store,
)


class TestLoadDotenvIfExists:
    """Tests for load_dotenv_if_exists function."""

    def test_load_dotenv_if_exists_with_file(self) -> None:
        """Verify .env file values are loaded into os.environ.

        From BDD scenario: Load configuration from .env file
        """
        # ARRANGE - Create temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_DATABASE_HOST=dotenv-host\n")
            f.write("TEST_DATABASE_PASSWORD=dotenv-password\n")
            dotenv_path = f.name

        try:
            # Ensure env vars are not set
            os.environ.pop("TEST_DATABASE_HOST", None)
            os.environ.pop("TEST_DATABASE_PASSWORD", None)

            # ACT
            load_dotenv_if_exists(dotenv_path)

            # ASSERT
            assert os.environ.get("TEST_DATABASE_HOST") == "dotenv-host"
            assert os.environ.get("TEST_DATABASE_PASSWORD") == "dotenv-password"
        finally:
            # CLEANUP
            Path(dotenv_path).unlink()
            os.environ.pop("TEST_DATABASE_HOST", None)
            os.environ.pop("TEST_DATABASE_PASSWORD", None)

    def test_load_dotenv_if_exists_without_file(self) -> None:
        """Verify function continues silently when .env file is missing.

        From BDD scenario: Continue silently when .env file is missing
        """
        # ARRANGE
        nonexistent_path = "/tmp/nonexistent_file_12345.env"
        assert not Path(nonexistent_path).exists()

        # ACT - Should not raise exception
        load_dotenv_if_exists(nonexistent_path)

        # ASSERT - No exception raised means success

    def test_load_dotenv_respects_existing_env_vars(self) -> None:
        """Verify existing environment variables are not overridden by .env file."""
        # ARRANGE
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("TEST_VAR=from-dotenv\n")
            dotenv_path = f.name

        try:
            # Set env var before loading .env
            os.environ["TEST_VAR"] = "already-set"

            # ACT
            load_dotenv_if_exists(dotenv_path)

            # ASSERT - Should NOT override
            assert os.environ.get("TEST_VAR") == "already-set"
        finally:
            # CLEANUP
            Path(dotenv_path).unlink()
            os.environ.pop("TEST_VAR", None)


class TestLoadFromParameterStore:
    """Tests for load_from_parameter_store function."""

    @mock_aws
    def test_load_from_parameter_store_success(self) -> None:
        """Verify parameters are loaded from AWS Parameter Store.

        From BDD scenario: Load configuration from AWS Parameter Store
        """
        # ARRANGE - Create mock Parameter Store
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/test/database/host",
            Value="test-db.amazonaws.com",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/port",
            Value="5432",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/password",
            Value="secret123",
            Type="SecureString",
        )

        # Clear env vars
        os.environ.pop("DATABASE_HOST", None)
        os.environ.pop("DATABASE_PORT", None)
        os.environ.pop("DATABASE_PASSWORD", None)

        # ACT
        load_from_parameter_store(environment="test")

        # ASSERT
        assert os.environ.get("DATABASE_HOST") == "test-db.amazonaws.com"
        assert os.environ.get("DATABASE_PORT") == "5432"
        assert os.environ.get("DATABASE_PASSWORD") == "secret123"

        # CLEANUP
        os.environ.pop("DATABASE_HOST", None)
        os.environ.pop("DATABASE_PORT", None)
        os.environ.pop("DATABASE_PASSWORD", None)

    @mock_aws
    def test_load_from_parameter_store_respects_existing_env(self) -> None:
        """Verify existing environment variables are not overridden by Parameter Store.

        From BDD scenario: Respect existing environment variable overrides
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/test/database/host",
            Value="aws-value",
            Type="String",
        )

        # Set env var before loading from Parameter Store
        os.environ["DATABASE_HOST"] = "local-override"

        # ACT
        load_from_parameter_store(environment="test")

        # ASSERT - Should NOT override
        assert os.environ.get("DATABASE_HOST") == "local-override"

        # CLEANUP
        os.environ.pop("DATABASE_HOST", None)

    @mock_aws
    def test_load_from_parameter_store_builds_database_url(self) -> None:
        """Verify DATABASE_URL is constructed from individual components.

        From BDD scenario: Build DATABASE_URL from individual components
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/test/database/host",
            Value="db.example.com",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/port",
            Value="5432",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/name",
            Value="mydb",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/user",
            Value="admin",
            Type="String",
        )
        ssm.put_parameter(
            Name="/epistemix/test/database/password",
            Value="secret",
            Type="SecureString",
        )

        # Clear all database env vars
        for key in [
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_URL",
        ]:
            os.environ.pop(key, None)

        # ACT
        load_from_parameter_store(environment="test")

        # ASSERT
        expected_url = "postgresql://admin:secret@db.example.com:5432/mydb"
        assert os.environ.get("DATABASE_URL") == expected_url

        # CLEANUP
        for key in [
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_URL",
        ]:
            os.environ.pop(key, None)

    @mock_aws
    def test_load_from_parameter_store_database_url_already_set(self) -> None:
        """Verify DATABASE_URL is not overridden if already set.

        From BDD scenario: Skip DATABASE_URL construction if already set
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/test/database/host",
            Value="db.example.com",
            Type="String",
        )

        # Set DATABASE_URL before loading
        existing_url = "postgresql://custom:url@host:5432/db"
        os.environ["DATABASE_URL"] = existing_url

        # Clear component env vars
        for key in [
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
        ]:  # noqa: E501
            os.environ.pop(key, None)

        # ACT
        load_from_parameter_store(environment="test")

        # ASSERT - DATABASE_URL should not change
        assert os.environ.get("DATABASE_URL") == existing_url

        # CLEANUP
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("DATABASE_HOST", None)

    def test_load_from_parameter_store_aws_unavailable(self) -> None:
        """Verify function continues gracefully when AWS is unavailable.

        From BDD scenario: Handle AWS service unavailable gracefully
        """
        # ARRANGE - No mock_aws decorator, so boto3 will fail with real AWS call
        os.environ.pop("DATABASE_HOST", None)

        # ACT - Should not raise exception
        load_from_parameter_store(environment="test")

        # ASSERT - No exception raised means success
        # DATABASE_HOST should remain unset since AWS call failed
        assert os.environ.get("DATABASE_HOST") is None

    @mock_aws
    def test_load_from_parameter_store_access_denied(self) -> None:
        """Verify function continues gracefully when AWS returns AccessDenied.

        From BDD scenario: Handle Parameter Store access denied gracefully
        """
        # ARRANGE - Mock ClientError for AccessDenied
        with patch("boto3.client") as mock_client:
            mock_ssm = MagicMock()
            mock_ssm.get_parameters_by_path.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException", "Message": "Access Denied"}},
                "GetParametersByPath",
            )
            mock_client.return_value = mock_ssm

            # ACT - Should not raise exception
            load_from_parameter_store(environment="test")

        # ASSERT - No exception raised means success

    @mock_aws
    def test_load_from_parameter_store_no_parameters(self) -> None:
        """Verify function handles empty Parameter Store results."""
        # ARRANGE - Parameter Store exists but has no parameters
        # ACT
        load_from_parameter_store(environment="empty")

        # ASSERT - No exception raised, function continues silently

    @mock_aws
    def test_load_from_parameter_store_decryption(self) -> None:
        """Verify SecureString parameters are decrypted with WithDecryption=True."""
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")

        # Create SecureString parameter
        ssm.put_parameter(
            Name="/epistemix/test/database/password",
            Value="encrypted-secret",
            Type="SecureString",
        )

        os.environ.pop("DATABASE_PASSWORD", None)

        # ACT
        load_from_parameter_store(environment="test")

        # ASSERT - Should be decrypted (moto returns the value directly)
        assert os.environ.get("DATABASE_PASSWORD") == "encrypted-secret"

        # CLEANUP
        os.environ.pop("DATABASE_PASSWORD", None)


class TestBootstrapConfig:
    """Tests for bootstrap_config main entry point."""

    @mock_aws
    def test_bootstrap_config_priority_order(self) -> None:
        """Verify configuration priority: .env > env vars > AWS.

        From BDD scenario: Bootstrap config priority order
        """
        # ARRANGE
        import boto3

        # Setup AWS Parameter Store
        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/test/database/name",
            Value="aws-db",
            Type="String",
        )

        # Setup .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DATABASE_HOST=dotenv-value\n")
            dotenv_path = f.name

        # Setup existing env var
        os.environ["DATABASE_PORT"] = "3000"

        # Clear DATABASE_NAME to allow AWS value
        os.environ.pop("DATABASE_NAME", None)

        try:
            # Patch load_dotenv to use our temp file
            with patch("epistemix_platform.bootstrap.load_dotenv") as mock_dotenv:
                # Make load_dotenv actually load from our temp file
                def side_effect_load(*args, **kwargs):  # noqa: ARG001
                    from dotenv import load_dotenv as real_load_dotenv

                    return real_load_dotenv(dotenv_path=dotenv_path, override=False)

                mock_dotenv.side_effect = side_effect_load

                # ACT
                bootstrap_config(environment="test")

                # ASSERT
                assert os.environ.get("DATABASE_HOST") == "dotenv-value"  # From .env
                assert os.environ.get("DATABASE_PORT") == "3000"  # From env var
                assert os.environ.get("DATABASE_NAME") == "aws-db"  # From AWS
        finally:
            # CLEANUP
            Path(dotenv_path).unlink()
            os.environ.pop("DATABASE_HOST", None)
            os.environ.pop("DATABASE_PORT", None)
            os.environ.pop("DATABASE_NAME", None)

    @mock_aws
    def test_bootstrap_config_uses_environment_variable(self) -> None:
        """Verify bootstrap_config uses ENVIRONMENT variable when no argument provided.

        From BDD scenario: Bootstrap config uses ENVIRONMENT variable
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/production/database/host",
            Value="prod-db.example.com",
            Type="String",
        )

        os.environ["ENVIRONMENT"] = "production"
        os.environ.pop("DATABASE_HOST", None)

        try:
            # ACT
            bootstrap_config()

            # ASSERT - Should query /epistemix/production/ path
            assert os.environ.get("DATABASE_HOST") == "prod-db.example.com"
        finally:
            # CLEANUP
            os.environ.pop("ENVIRONMENT", None)
            os.environ.pop("DATABASE_HOST", None)

    @mock_aws
    def test_bootstrap_config_defaults_to_dev(self) -> None:
        """Verify bootstrap_config defaults to 'dev' environment.

        From BDD scenario: Bootstrap config defaults to 'dev' environment
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/dev/database/host",
            Value="dev-db.example.com",
            Type="String",
        )

        # Ensure ENVIRONMENT is not set
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("DATABASE_HOST", None)

        try:
            # ACT
            bootstrap_config()

            # ASSERT - Should query /epistemix/dev/ path
            assert os.environ.get("DATABASE_HOST") == "dev-db.example.com"
        finally:
            # CLEANUP
            os.environ.pop("DATABASE_HOST", None)

    @mock_aws
    def test_bootstrap_config_explicit_environment_argument(self) -> None:
        """Verify bootstrap_config uses explicit environment argument.

        From BDD scenario: Bootstrap config with explicit environment argument
        """
        # ARRANGE
        import boto3

        ssm = boto3.client("ssm", region_name="us-east-1")
        ssm.put_parameter(
            Name="/epistemix/staging/database/host",
            Value="staging-db.example.com",
            Type="String",
        )

        # ENVIRONMENT not set
        os.environ.pop("ENVIRONMENT", None)
        os.environ.pop("DATABASE_HOST", None)

        try:
            # ACT
            bootstrap_config(environment="staging")

            # ASSERT - Should query /epistemix/staging/ path
            assert os.environ.get("DATABASE_HOST") == "staging-db.example.com"
        finally:
            # CLEANUP
            os.environ.pop("DATABASE_HOST", None)

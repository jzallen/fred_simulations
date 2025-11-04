"""Tests for RDS IAM authentication.

Based on synthesis of three engineer prototypes:
- ENGINEER-01: Security rigor (SSL, validation, no logging)
- ENGINEER-02: Simplicity (minimal code, backwards compat)
- ENGINEER-03: Performance monitoring (instrumentation)
"""

import os
from unittest.mock import Mock, patch

import pytest

from epistemix_platform.repositories.database import (
    create_engine_from_config,
    create_postgresql_engine_with_iam,
)


class TestIAMAuthTokenGeneration:
    """Test IAM authentication token generation flow."""

    def test_generates_iam_token_and_creates_engine(self, mock_config):
        """Verify IAM token generation and engine creation."""
        with patch("boto3.client") as mock_boto3, patch(
            "epistemix_platform.repositories.database.create_engine"
        ) as mock_create_engine:
            mock_rds = Mock()
            mock_boto3.return_value = mock_rds
            mock_rds.generate_db_auth_token.return_value = "test-token-abc123"
            mock_create_engine.return_value = Mock()

            engine = create_postgresql_engine_with_iam(
                host="test.rds.amazonaws.com",
                port=5432,
                database="testdb",
                user="testuser",
                region="us-east-1",
                config=mock_config,
            )

            # Verify boto3 called correctly
            mock_boto3.assert_called_once_with("rds", region_name="us-east-1")
            mock_rds.generate_db_auth_token.assert_called_once_with(
                DBHostname="test.rds.amazonaws.com",
                Port=5432,
                DBUsername="testuser",
                Region="us-east-1",
            )

            # Verify engine created
            assert engine is not None

    def test_token_used_as_password_in_connection_url(self, mock_config):
        """Verify token is used as password in PostgreSQL URL."""
        with patch("boto3.client") as mock_boto3:
            mock_rds = Mock()
            mock_boto3.return_value = mock_rds
            mock_rds.generate_db_auth_token.return_value = "token123"

            with patch(
                "epistemix_platform.repositories.database.create_engine"
            ) as mock_create_engine:
                create_postgresql_engine_with_iam(
                    host="test.rds.amazonaws.com",
                    port=5432,
                    database="testdb",
                    user="testuser",
                    region="us-east-1",
                    config=mock_config,
                )

                # Verify connection URL contains token as password
                call_args = mock_create_engine.call_args
                connection_url = call_args[0][0]
                assert "testuser:token123@test.rds.amazonaws.com" in connection_url
                assert ":5432/testdb" in connection_url

    def test_ssl_required_in_connect_args(self, mock_config):
        """Verify SSL is required for IAM auth (security requirement)."""
        with patch("boto3.client") as mock_boto3:
            mock_rds = Mock()
            mock_boto3.return_value = mock_rds
            mock_rds.generate_db_auth_token.return_value = "token"

            with patch(
                "epistemix_platform.repositories.database.create_engine"
            ) as mock_create_engine:
                create_postgresql_engine_with_iam(
                    host="test.rds.amazonaws.com",
                    port=5432,
                    database="testdb",
                    user="testuser",
                    region="us-east-1",
                    config=mock_config,
                )

                # Verify SSL required
                call_args = mock_create_engine.call_args
                connect_args = call_args[1]["connect_args"]
                assert connect_args["sslmode"] == "require"

    def test_pool_pre_ping_enabled(self, mock_config):
        """Verify pool_pre_ping enabled to handle token expiration."""
        with patch("boto3.client") as mock_boto3:
            mock_rds = Mock()
            mock_boto3.return_value = mock_rds
            mock_rds.generate_db_auth_token.return_value = "token"

            with patch(
                "epistemix_platform.repositories.database.create_engine"
            ) as mock_create_engine:
                create_postgresql_engine_with_iam(
                    host="test.rds.amazonaws.com",
                    port=5432,
                    database="testdb",
                    user="testuser",
                    region="us-east-1",
                    config=mock_config,
                )

                # Verify pool_pre_ping enabled
                call_args = mock_create_engine.call_args
                assert call_args[1]["pool_pre_ping"] is True


class TestFactoryDelegation:
    """Test factory function delegation to IAM auth."""

    def test_use_iam_auth_delegates_to_iam_function(self, mock_config):
        """Verify USE_IAM_AUTH=true triggers IAM authentication."""
        with patch.dict(
            os.environ,
            {
                "USE_IAM_AUTH": "true",
                "DATABASE_HOST": "test.rds.amazonaws.com",
                "DATABASE_PORT": "5432",
                "DATABASE_NAME": "testdb",
                "DATABASE_IAM_USER": "testuser",
                "AWS_REGION": "us-east-1",
            },
        ), patch(
            "epistemix_platform.repositories.database.create_postgresql_engine_with_iam"
        ) as mock_iam:
            mock_iam.return_value = Mock()
            create_engine_from_config(config=mock_config)

            # Verify IAM function was called
            mock_iam.assert_called_once()
            # Get positional arguments
            call_args = mock_iam.call_args[0]
            assert call_args[0] == "test.rds.amazonaws.com"  # host
            assert call_args[1] == 5432  # port
            assert call_args[2] == "testdb"  # database
            assert call_args[3] == "testuser"  # user
            assert call_args[4] == "us-east-1"  # region

    def test_missing_database_host_raises_error(self, mock_config):
        """Verify missing DATABASE_HOST raises clear error."""
        with patch.dict(
            os.environ,
            {
                "USE_IAM_AUTH": "true",
                "DATABASE_NAME": "testdb",
                "DATABASE_IAM_USER": "testuser",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="IAM authentication requires"):
                create_engine_from_config(config=mock_config)

    def test_missing_database_name_raises_error(self, mock_config):
        """Verify missing DATABASE_NAME raises clear error."""
        with patch.dict(
            os.environ,
            {
                "USE_IAM_AUTH": "true",
                "DATABASE_HOST": "test.rds.amazonaws.com",
                "DATABASE_IAM_USER": "testuser",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="IAM authentication requires"):
                create_engine_from_config(config=mock_config)

    def test_missing_database_iam_user_raises_error(self, mock_config):
        """Verify missing DATABASE_IAM_USER raises clear error."""
        with patch.dict(
            os.environ,
            {
                "USE_IAM_AUTH": "true",
                "DATABASE_HOST": "test.rds.amazonaws.com",
                "DATABASE_NAME": "testdb",
            },
            clear=True,
        ):
            with pytest.raises(ValueError, match="IAM authentication requires"):
                create_engine_from_config(config=mock_config)


class TestBackwardsCompatibility:
    """Test that IAM auth doesn't break existing functionality."""

    def test_password_auth_still_works(self, mock_config):
        """Verify traditional password auth unchanged."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "epistemix_platform.repositories.database.create_postgresql_engine"
            ) as mock_pg:
                create_engine_from_config(
                    config=mock_config, database_url="postgresql://user:pass@host:5432/db"
                )

                # Verify password function was called (not IAM)
                mock_pg.assert_called_once()

    def test_sqlite_still_works(self, mock_config):
        """Verify SQLite connections unchanged."""
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "epistemix_platform.repositories.database.create_sqlite_engine"
            ) as mock_sqlite:
                create_engine_from_config(config=mock_config, database_url="sqlite:///test.db")

                # Verify SQLite function was called (not IAM)
                mock_sqlite.assert_called_once()


class TestRollback:
    """Test that rollback is trivial."""

    def test_removing_use_iam_auth_env_var_reverts_to_password(self, mock_config):
        """Verify removing USE_IAM_AUTH reverts to password auth."""
        # Simulate initial state with IAM enabled
        with patch.dict(
            os.environ,
            {
                "USE_IAM_AUTH": "true",
                "DATABASE_HOST": "test.rds.amazonaws.com",
                "DATABASE_NAME": "testdb",
                "DATABASE_IAM_USER": "testuser",
            },
        ):
            with patch(
                "epistemix_platform.repositories.database.create_postgresql_engine_with_iam"
            ):
                create_engine_from_config(config=mock_config)

        # Simulate rollback (remove USE_IAM_AUTH)
        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "epistemix_platform.repositories.database.create_postgresql_engine"
            ) as mock_pg:
                create_engine_from_config(
                    config=mock_config, database_url="postgresql://user:pass@host:5432/db"
                )

                # Verify reverted to password auth
                mock_pg.assert_called_once()


class TestSecurityRequirements:
    """Test security requirements for IAM authentication."""

    def test_token_never_appears_in_logs(self, mock_config, caplog):
        """Verify IAM token is never logged (security requirement)."""
        with patch("boto3.client") as mock_boto3, patch(
            "epistemix_platform.repositories.database.create_engine"
        ) as mock_create_engine:
            mock_rds = Mock()
            mock_boto3.return_value = mock_rds
            mock_rds.generate_db_auth_token.return_value = "SECRET_TOKEN_12345"
            mock_create_engine.return_value = Mock()

            with caplog.at_level("DEBUG"):
                create_postgresql_engine_with_iam(
                    host="test.rds.amazonaws.com",
                    port=5432,
                    database="testdb",
                    user="testuser",
                    region="us-east-1",
                    config=mock_config,
                )

            # Verify token doesn't appear in any log message
            assert "SECRET_TOKEN_12345" not in caplog.text


# Fixtures


@pytest.fixture
def mock_config():
    """Mock Config object for testing."""
    config = Mock()
    config.DATABASE_POOL_SIZE = 10
    config.DATABASE_MAX_OVERFLOW = 5
    config.DATABASE_POOL_TIMEOUT = 30
    return config

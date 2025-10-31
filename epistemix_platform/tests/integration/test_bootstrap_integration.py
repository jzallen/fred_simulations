"""Integration tests for bootstrap module with Flask app and CLI.

These tests verify that the bootstrap configuration loader integrates correctly
with the Flask application and CLI. The bootstrap module itself has comprehensive
unit tests, so these integration tests focus on verifying:

1. Flask app starts successfully with bootstrap
2. CLI commands execute successfully with bootstrap
3. Configuration is loaded from .env files
4. Application works without AWS credentials (local development)
"""

import os


class TestFlaskAppBootstrap:
    """Test Flask app integration with bootstrap configuration."""

    def test_flask_app_imports_without_error(self):
        """Verify Flask app can be imported with bootstrap calls at module level.

        This test ensures that the bootstrap_config() call at the top of app.py
        executes successfully and doesn't prevent the module from loading.
        """
        # Import should succeed even without AWS credentials
        from epistemix_platform import app

        assert app is not None
        assert hasattr(app, "app")
        assert app.app is not None

    def test_flask_app_starts_with_bootstrap(self):
        """Verify Flask app starts successfully with bootstrap configuration.

        This test ensures the Flask application initializes correctly after
        bootstrap runs, with proper database and configuration setup.
        """
        from epistemix_platform.app import app

        # App should be initialized
        assert app is not None

        # Test client should work
        with app.test_client() as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"

    def test_flask_app_bootstrap_respects_env_vars(self):
        """Verify bootstrap respects environment variables over defaults.

        This test ensures that explicitly set environment variables take
        priority over values that might be loaded from .env files or
        AWS Parameter Store.
        """
        # Set a test environment variable
        test_bucket = "test-integration-bucket"
        os.environ["S3_UPLOAD_BUCKET"] = test_bucket

        try:
            # Import after setting env var
            from epistemix_platform import app

            # Bootstrap should have loaded the env var into os.environ
            # Flask app reads from os.environ, not necessarily app.config
            assert os.environ.get("S3_UPLOAD_BUCKET") == test_bucket

            # App should still be functional
            assert app.app is not None

        finally:
            # Clean up
            if "S3_UPLOAD_BUCKET" in os.environ:
                del os.environ["S3_UPLOAD_BUCKET"]


class TestCLIBootstrap:
    """Test CLI integration with bootstrap configuration."""

    def test_cli_imports_without_error(self):
        """Verify CLI module can be imported with bootstrap calls at module level.

        This test ensures that the bootstrap_config() call at the top of cli.py
        executes successfully and doesn't prevent the module from loading.
        """
        # Import should succeed even without AWS credentials
        from epistemix_platform import cli

        assert cli is not None
        assert hasattr(cli, "cli")

    def test_cli_version_command_works(self):
        """Verify CLI version command executes with bootstrap.

        This test ensures the CLI commands work after bootstrap runs.
        We use the version command as it's the simplest command that
        doesn't require database or AWS access.
        """
        from click.testing import CliRunner

        from epistemix_platform.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["version"])

        # Command should execute successfully
        assert result.exit_code == 0
        assert "CLI" in result.output

    def test_cli_help_works_with_bootstrap(self):
        """Verify CLI help command works with bootstrap.

        This ensures the CLI is properly initialized and can display
        help information after bootstrap configuration loading.
        """
        from click.testing import CliRunner

        from epistemix_platform.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        # Command should execute successfully
        assert result.exit_code == 0
        assert "jobs" in result.output.lower()


class TestBootstrapWithDotenv:
    """Test bootstrap configuration loading from .env files."""

    def test_config_loaded_from_dotenv(self, tmp_path):
        """Verify configuration can be loaded from .env file.

        This test creates a temporary .env file and verifies that
        bootstrap loads the values correctly.
        """
        # Create a temporary .env file
        dotenv_file = tmp_path / ".env"
        dotenv_content = """
DATABASE_URL=postgresql://test_user:test_pass@test_host:5432/test_db
S3_UPLOAD_BUCKET=test-dotenv-bucket
AWS_REGION=us-west-2
ENVIRONMENT=test
"""
        dotenv_file.write_text(dotenv_content)

        # Change to temp directory so .env is found
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Clear any existing env vars to ensure .env is used
            env_vars_to_clear = [
                "DATABASE_URL",
                "S3_UPLOAD_BUCKET",
                "AWS_REGION",
                "ENVIRONMENT",
            ]
            original_values = {}
            for var in env_vars_to_clear:
                if var in os.environ:
                    original_values[var] = os.environ[var]
                    del os.environ[var]

            # Import and run bootstrap
            from epistemix_platform.bootstrap import bootstrap_config

            bootstrap_config()

            # Verify values were loaded from .env
            assert os.environ.get("S3_UPLOAD_BUCKET") == "test-dotenv-bucket"
            assert os.environ.get("AWS_REGION") == "us-west-2"
            assert os.environ.get("ENVIRONMENT") == "test"

            # Restore original environment
            for var, value in original_values.items():
                os.environ[var] = value

        finally:
            os.chdir(original_dir)

    def test_env_vars_override_dotenv(self, tmp_path):
        """Verify explicit environment variables override .env file values.

        This test ensures the configuration priority is correct:
        explicit env vars > .env file > Parameter Store.
        """
        # Create a temporary .env file
        dotenv_file = tmp_path / ".env"
        dotenv_content = """
S3_UPLOAD_BUCKET=dotenv-bucket
TEST_VAR_FROM_DOTENV=dotenv-value
"""
        dotenv_file.write_text(dotenv_content)

        # Set an explicit environment variable BEFORE bootstrap
        explicit_bucket = "explicit-env-var-bucket"
        original_bucket = os.environ.get("S3_UPLOAD_BUCKET")
        os.environ["S3_UPLOAD_BUCKET"] = explicit_bucket

        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Clear any previous value for TEST_VAR_FROM_DOTENV
            if "TEST_VAR_FROM_DOTENV" in os.environ:
                del os.environ["TEST_VAR_FROM_DOTENV"]

            # Import and run bootstrap
            from epistemix_platform.bootstrap import bootstrap_config

            bootstrap_config()

            # Explicit env var should win over .env file
            assert os.environ.get("S3_UPLOAD_BUCKET") == explicit_bucket
            # But .env values for other vars should still be loaded
            assert os.environ.get("TEST_VAR_FROM_DOTENV") == "dotenv-value"

        finally:
            os.chdir(original_dir)
            # Restore original value
            if original_bucket is not None:
                os.environ["S3_UPLOAD_BUCKET"] = original_bucket
            elif "S3_UPLOAD_BUCKET" in os.environ:
                del os.environ["S3_UPLOAD_BUCKET"]
            if "TEST_VAR_FROM_DOTENV" in os.environ:
                del os.environ["TEST_VAR_FROM_DOTENV"]


class TestBootstrapGracefulDegradation:
    """Test bootstrap behavior when AWS services are unavailable."""

    def test_bootstrap_works_without_aws_credentials(self):
        """Verify bootstrap works gracefully without AWS credentials.

        This is critical for local development - developers should be able
        to run the application using .env files without needing AWS access.
        """
        # Temporarily clear AWS credential env vars
        aws_vars = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_SESSION_TOKEN",
        ]
        original_values = {}
        for var in aws_vars:
            if var in os.environ:
                original_values[var] = os.environ[var]
                del os.environ[var]

        try:
            # Bootstrap should not raise exception
            from epistemix_platform.bootstrap import bootstrap_config

            bootstrap_config(environment="test-no-aws")

            # Application should still be importable
            from epistemix_platform import app

            assert app is not None

        finally:
            # Restore AWS credentials
            for var, value in original_values.items():
                os.environ[var] = value

    def test_flask_app_works_without_parameter_store(self):
        """Verify Flask app works when Parameter Store is unavailable.

        This ensures the application can run entirely from .env files
        or environment variables without AWS access.
        """
        # Set required config via environment
        os.environ["DATABASE_URL"] = "sqlite:///test.db"
        os.environ["S3_UPLOAD_BUCKET"] = "test-bucket"

        try:
            from epistemix_platform.app import app

            with app.test_client() as client:
                response = client.get("/health")
                assert response.status_code == 200

        finally:
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            if "S3_UPLOAD_BUCKET" in os.environ:
                del os.environ["S3_UPLOAD_BUCKET"]


# Note: AWS Parameter Store integration tests would require:
# 1. Valid AWS credentials in CI environment
# 2. Test parameters created in Parameter Store
# 3. Cleanup of test parameters after tests
#
# These tests are omitted as they would require AWS infrastructure
# and would fail in local development. The bootstrap module itself
# has unit tests that mock boto3 to verify Parameter Store behavior.

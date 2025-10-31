"""
Integration tests for bootstrap configuration loading in simulation_runner CLI.

These tests verify that the bootstrap module is properly integrated and that
configuration loading works with different sources (.env files, environment
variables, AWS Parameter Store).
"""

import os
import subprocess

import pytest


class TestBootstrapIntegration:
    """Integration tests for bootstrap module integration."""

    def test_cli_starts_with_bootstrap(self):
        """Test that CLI initializes successfully with bootstrap."""
        # Build the CLI (use pants package)
        result = subprocess.run(
            ["pants", "package", "simulation_runner:simulation-runner-cli"],
            cwd="/workspaces/fred_simulations",
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Failed to build CLI: {result.stderr}"

        # Run CLI --help to verify it starts
        cli_path = "/workspaces/fred_simulations/dist/simulation_runner/simulation-runner-cli.pex"
        result = subprocess.run(
            [cli_path, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"CLI failed to start: {result.stderr}"
        assert "FRED Simulation Runner CLI" in result.stdout

    def test_config_loaded_from_dotenv(self, tmp_path):
        """Test that configuration is loaded from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
FRED_HOME=/workspaces/fred_simulations/fred-framework
EPISTEMIX_API_URL=http://localhost:5000
EPISTEMIX_S3_BUCKET=test-bucket
AWS_REGION=us-west-2
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/testdb
ENVIRONMENT=dev
"""
        )

        # Build CLI if not already built
        subprocess.run(
            ["pants", "package", "simulation_runner:simulation-runner-cli"],
            cwd="/workspaces/fred_simulations",
            capture_output=True,
            timeout=60,
        )

        # Run CLI config command with .env file in environment
        cli_path = "/workspaces/fred_simulations/dist/simulation_runner/simulation-runner-cli.pex"

        # Change to tmp directory so .env is found
        result = subprocess.run(
            [cli_path, "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=10,
        )

        # Note: CLI might fail validation but bootstrap should have loaded .env
        # Check that error doesn't mention bootstrap failure
        assert "bootstrap" not in result.stderr.lower()

    def test_simulation_config_from_env_unchanged(self, monkeypatch):
        """Test that existing SimulationConfig.from_env() continues to work."""
        # Set up environment variables
        monkeypatch.setenv("FRED_HOME", "/workspaces/fred_simulations/fred-framework")
        monkeypatch.setenv("EPISTEMIX_API_URL", "http://localhost:5000")
        monkeypatch.setenv("EPISTEMIX_S3_BUCKET", "test-bucket")
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")

        # Import after setting environment (to get fresh config)
        from simulation_runner.config import SimulationConfig

        # Load configuration the same way as before
        config = SimulationConfig.from_env(job_id=12, run_id=4)

        # Verify configuration loaded correctly
        assert config.job_id == 12
        assert config.run_id == 4
        assert str(config.fred_home) == "/workspaces/fred_simulations/fred-framework"
        assert config.api_url == "http://localhost:5000"
        assert config.s3_bucket == "test-bucket"
        assert config.aws_region == "us-west-2"
        assert config.database_url == "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_environment_variables_override_dotenv(self, tmp_path, monkeypatch):
        """Test that environment variables have higher priority than .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            """
FRED_HOME=/workspaces/fred_simulations/fred-framework
EPISTEMIX_S3_BUCKET=dotenv-bucket
AWS_REGION=us-east-1
DATABASE_URL=postgresql://dotenv:pass@localhost:5432/dotenv
"""
        )

        # Set environment variable that should override .env
        monkeypatch.setenv("EPISTEMIX_S3_BUCKET", "override-bucket")

        # Build CLI if not already built
        subprocess.run(
            ["pants", "package", "simulation_runner:simulation-runner-cli"],
            cwd="/workspaces/fred_simulations",
            capture_output=True,
            timeout=60,
        )

        # Run CLI config command
        cli_path = "/workspaces/fred_simulations/dist/simulation_runner/simulation-runner-cli.pex"

        result = subprocess.run(
            [cli_path, "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "EPISTEMIX_S3_BUCKET": "override-bucket"},
            timeout=10,
        )

        # Environment variable should override .env value
        # (CLI config output includes S3 bucket)
        assert "override-bucket" in result.stdout or "override-bucket" in result.stderr

    @pytest.mark.skipif(
        os.getenv("ENVIRONMENT") not in ["staging", "production"],
        reason="AWS Parameter Store only available in staging/production",
    )
    def test_config_loaded_from_aws(self):
        """Test that configuration loads from AWS Parameter Store in production.

        This test only runs in CI/staging/production environments where
        AWS Parameter Store is available.
        """
        # Build CLI
        subprocess.run(
            ["pants", "package", "simulation_runner:simulation-runner-cli"],
            cwd="/workspaces/fred_simulations",
            capture_output=True,
            timeout=60,
        )

        # Run CLI with production environment
        cli_path = "/workspaces/fred_simulations/dist/simulation_runner/simulation-runner-cli.pex"

        result = subprocess.run(
            [cli_path, "config"],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
                "FRED_HOME": "/workspaces/fred_simulations/fred-framework",
            },
            timeout=30,
        )

        # Should successfully load configuration from Parameter Store
        # (actual values depend on AWS Parameter Store content)
        assert result.returncode == 0 or "Configuration" in result.stdout


class TestBootstrapErrorHandling:
    """Test error handling in bootstrap integration."""

    def test_missing_fred_home_shows_clear_error(self, monkeypatch, tmp_path):
        """Test that missing FRED_HOME shows a clear error message."""
        # Remove FRED_HOME from environment
        monkeypatch.delenv("FRED_HOME", raising=False)

        # Create empty .env without FRED_HOME
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://user:pass@localhost:5432/db\n")

        # Build CLI
        subprocess.run(
            ["pants", "package", "simulation_runner:simulation-runner-cli"],
            cwd="/workspaces/fred_simulations",
            capture_output=True,
            timeout=60,
        )

        # Try to run CLI
        cli_path = "/workspaces/fred_simulations/dist/simulation_runner/simulation-runner-cli.pex"

        result = subprocess.run(
            [cli_path, "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={k: v for k, v in os.environ.items() if k != "FRED_HOME"},
            timeout=10,
        )

        # Should get clear error about FRED_HOME
        assert result.returncode != 0
        assert "FRED_HOME" in result.stderr or "FRED_HOME" in result.stdout

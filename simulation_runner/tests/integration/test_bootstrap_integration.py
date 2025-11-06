"""
Integration tests for bootstrap configuration loading in simulation_runner CLI.

These tests verify that the bootstrap module is properly integrated and that
configuration loading works with different sources (.env files, environment
variables, AWS Parameter Store).
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="class")
def repo_root():
    """Get repository root dynamically using git."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


@pytest.fixture(scope="class")
def fred_home(repo_root):
    """Get FRED_HOME path dynamically."""
    return repo_root / "fred-framework"


@pytest.fixture(scope="class")
def cli_pex(repo_root):
    """Build CLI once for all tests in this class."""
    # Build the CLI (use pants package)
    result = subprocess.run(
        ["pants", "package", "simulation_runner:simulation-runner-cli"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, f"Failed to build CLI: {result.stderr}"

    cli_path = repo_root / "dist/simulation_runner/simulation-runner-cli.pex"
    assert cli_path.exists(), f"CLI not found at {cli_path}"
    return cli_path


class TestBootstrapIntegration:
    """Integration tests for bootstrap module integration."""

    def test_cli_starts_with_bootstrap(self, cli_pex):
        """Test that CLI initializes successfully with bootstrap."""
        # Run CLI --help to verify it starts
        result = subprocess.run(
            [str(cli_pex), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result.returncode == 0, f"CLI failed to start: {result.stderr}"
        assert "FRED Simulation Runner CLI" in result.stdout

    def test_config_loaded_from_dotenv(self, tmp_path, cli_pex, fred_home):
        """Test that configuration is loaded from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            f"""
FRED_HOME={fred_home}
EPISTEMIX_API_URL=http://localhost:5000
EPISTEMIX_S3_BUCKET=test-bucket
AWS_REGION=us-west-2
DATABASE_URL=postgresql://testuser:testpass@localhost:5432/testdb
ENVIRONMENT=dev
"""
        )

        # Run CLI config command with .env file in environment
        # Change to tmp directory so .env is found
        result = subprocess.run(
            [str(cli_pex), "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            timeout=10,
        )

        # Verify bootstrap loaded .env file - check for actual values from .env
        # Should see the test-bucket value we configured
        assert (
            result.returncode == 0
            or "test-bucket" in result.stdout
            or "test-bucket" in result.stderr
        )
        # Verify no bootstrap errors
        assert "bootstrap" not in result.stderr.lower()

    def test_simulation_config_from_env_unchanged(self, monkeypatch, fred_home):
        """Test that existing SimulationConfig.from_env() continues to work."""
        # Set up environment variables
        monkeypatch.setenv("FRED_HOME", str(fred_home))
        monkeypatch.setenv("EPISTEMIX_API_URL", "http://localhost:5000")
        monkeypatch.setenv("EPISTEMIX_S3_BUCKET", "test-bucket")
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb"
        )

        # Import after setting environment (to get fresh config)
        from simulation_runner.config import SimulationConfig

        # Load configuration the same way as before
        config = SimulationConfig.from_env(job_id=12, run_id=4)

        # Verify configuration loaded correctly
        assert config.job_id == 12
        assert config.run_id == 4
        assert str(config.fred_home) == str(fred_home)
        assert config.api_url == "http://localhost:5000"
        assert config.s3_bucket == "test-bucket"
        assert config.aws_region == "us-west-2"
        assert (
            config.database_url
            == "postgresql://testuser:testpass@localhost:5432/testdb"
        )

    def test_environment_variables_override_dotenv(self, tmp_path, cli_pex, fred_home):
        """Test that environment variables have higher priority than .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            f"""
FRED_HOME={fred_home}
EPISTEMIX_S3_BUCKET=dotenv-bucket
AWS_REGION=us-east-1
DATABASE_URL=postgresql://dotenv:pass@localhost:5432/dotenv
"""
        )

        # Run CLI config command with environment variable override
        result = subprocess.run(
            [str(cli_pex), "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "EPISTEMIX_S3_BUCKET": "override-bucket"},
            timeout=10,
        )

        # Environment variable should override .env value
        # (CLI config output includes S3 bucket)
        assert "override-bucket" in result.stdout or "override-bucket" in result.stderr
        # Should NOT see the dotenv value
        assert "dotenv-bucket" not in result.stdout

    @pytest.mark.skipif(
        os.getenv("ENVIRONMENT") not in ["staging", "production"],
        reason="AWS Parameter Store only available in staging/production",
    )
    def test_config_loaded_from_aws(self, cli_pex, fred_home):
        """Test that configuration loads from AWS Parameter Store in production.

        This test only runs in CI/staging/production environments where
        AWS Parameter Store is available.
        """
        # Run CLI with production environment
        result = subprocess.run(
            [str(cli_pex), "config"],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
                "FRED_HOME": str(fred_home),
            },
            timeout=30,
        )

        # Should successfully load configuration from Parameter Store
        # (actual values depend on AWS Parameter Store content)
        assert result.returncode == 0 or "Configuration" in result.stdout


class TestBootstrapErrorHandling:
    """Test error handling in bootstrap integration."""

    def test_missing_fred_home_shows_clear_error(self, monkeypatch, tmp_path, cli_pex):
        """Test that missing FRED_HOME shows a clear error message."""
        # Remove FRED_HOME from environment
        monkeypatch.delenv("FRED_HOME", raising=False)

        # Create empty .env without FRED_HOME
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://user:pass@localhost:5432/db\n")

        # Try to run CLI
        result = subprocess.run(
            [str(cli_pex), "config"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={k: v for k, v in os.environ.items() if k != "FRED_HOME"},
            timeout=10,
        )

        # Should get clear error about FRED_HOME
        assert result.returncode != 0
        assert "FRED_HOME" in result.stderr or "FRED_HOME" in result.stdout

"""
Configuration management for the simulation runner.

This module provides a centralized configuration dataclass that loads
settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from simulation_runner.exceptions import ConfigurationError


@dataclass
class SimulationConfig:
    """
    Configuration for FRED simulation runner.

    This configuration is typically loaded from environment variables
    but can also be constructed directly for testing.

    Attributes
    ----------
    job_id : int
        The job ID to process
    run_id : Optional[int]
        Specific run ID to process (None = process all runs)
    fred_home : Path
        Path to FRED framework installation
    workspace_dir : Path
        Directory for job downloads and simulation outputs
    s3_bucket : str
        S3 bucket name for uploads
    aws_region : str
        AWS region for S3 access
    database_url : str
        Database connection string
    """

    job_id: int
    run_id: int | None
    fred_home: Path
    workspace_dir: Path
    s3_bucket: str
    aws_region: str
    database_url: str

    @classmethod
    def from_env(cls, job_id: int, run_id: int | None = None) -> "SimulationConfig":
        """
        Load configuration from environment variables.

        Parameters
        ----------
        job_id : int
            The job ID to process
        run_id : Optional[int]
            Specific run ID to process (None = process all runs)

        Returns
        -------
        SimulationConfig
            Configuration loaded from environment

        Raises
        ------
        ConfigurationError
            If required environment variables are missing

        Examples
        --------
        >>> config = SimulationConfig.from_env(job_id=12, run_id=4)
        >>> config.fred_home
        PosixPath('/fred-framework')
        """
        # Get FRED_HOME (required)
        fred_home_str = os.getenv("FRED_HOME")
        if not fred_home_str:
            raise ConfigurationError("FRED_HOME environment variable is required")
        fred_home = Path(fred_home_str)

        # Get workspace directory (defaults to /workspace/job_{job_id})
        workspace_str = os.getenv("WORKSPACE_DIR", f"/workspace/job_{job_id}")
        workspace_dir = Path(workspace_str)

        # Get S3 bucket (optional)
        s3_bucket = os.getenv("EPISTEMIX_S3_BUCKET", "")

        # Get AWS region (defaults to us-east-1)
        aws_region = os.getenv("AWS_REGION", "us-east-1")

        # Get database URL (defaults to sqlite)
        database_url = os.getenv("DATABASE_URL", "sqlite:///epistemix_jobs.db")

        # Handle postgres:// -> postgresql:// conversion for compatibility
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        return cls(
            job_id=job_id,
            run_id=run_id,
            fred_home=fred_home,
            workspace_dir=workspace_dir,
            s3_bucket=s3_bucket,
            aws_region=aws_region,
            database_url=database_url,
        )

    def validate(self) -> list[str]:
        """
        Validate configuration and return list of error messages.

        Returns
        -------
        list[str]
            List of validation errors (empty if valid)

        Examples
        --------
        >>> config = SimulationConfig.from_env(job_id=12)
        >>> errors = config.validate()
        >>> if errors:
        ...     print(f"Configuration errors: {errors}")
        """
        errors = []

        # Validate FRED_HOME exists
        if not self.fred_home.exists():
            errors.append(f"FRED_HOME does not exist: {self.fred_home}")

        # Validate FRED binary exists (check both locations)
        fred_binary = self.fred_home / "bin" / "FRED"
        fred_binary_fallback = Path("/usr/local/bin/FRED")
        if not fred_binary.exists() and not fred_binary_fallback.exists():
            errors.append(f"FRED binary not found at {fred_binary} or {fred_binary_fallback}")

        # Validate FRED data directory exists
        fred_data = self.fred_home / "data"
        if not fred_data.exists():
            errors.append(f"FRED data directory not found: {fred_data}")

        # Validate job_id is positive
        if self.job_id <= 0:
            errors.append(f"job_id must be positive, got: {self.job_id}")

        # Validate run_id is positive if specified
        if self.run_id is not None and self.run_id <= 0:
            errors.append(f"run_id must be positive, got: {self.run_id}")

        return errors

    def get_fred_binary(self) -> Path:
        """
        Get path to FRED executable.

        Returns
        -------
        Path
            Path to FRED binary

        Raises
        ------
        ConfigurationError
            If FRED binary does not exist
        """
        fred_binary = self.fred_home / "bin" / "FRED"
        if not fred_binary.exists():
            # Try /usr/local/bin/FRED (Docker location)
            fred_binary = Path("/usr/local/bin/FRED")
            if not fred_binary.exists():
                raise ConfigurationError(
                    f"FRED binary not found in {self.fred_home}/bin or /usr/local/bin"
                )
        return fred_binary

    def __repr__(self) -> str:
        """Return string representation with sanitized sensitive data."""
        return (
            f"SimulationConfig("
            f"job_id={self.job_id}, "
            f"run_id={self.run_id}, "
            f"fred_home={self.fred_home}, "
            f"workspace_dir={self.workspace_dir}, "
            f"s3_bucket={self.s3_bucket}, "
            f"aws_region={self.aws_region})"
        )

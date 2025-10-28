"""
Custom exceptions for the simulation runner.

These exceptions provide structured error handling throughout the
simulation workflow, enabling better error reporting and recovery.
"""


class SimulationRunnerError(Exception):
    """Base class for all simulation runner errors."""

    pass


class ConfigurationError(SimulationRunnerError):
    """Error in simulation configuration."""

    pass


class DownloadError(SimulationRunnerError):
    """Failed to download job uploads from S3."""

    pass


class ExtractionError(SimulationRunnerError):
    """Failed to extract archive files."""

    pass


class FREDConfigError(SimulationRunnerError):
    """Failed to prepare FRED configuration file."""

    pass


class ValidationError(SimulationRunnerError):
    """FRED configuration validation failed."""

    pass


class SimulationError(SimulationRunnerError):
    """FRED simulation execution failed."""

    pass


class UploadError(SimulationRunnerError):
    """Failed to upload simulation results to S3."""

    pass


class WorkflowError(SimulationRunnerError):
    """General workflow execution error."""

    pass

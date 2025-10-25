"""
Domain exceptions for the Epistemix platform.

This module defines the exception hierarchy for results upload operations,
following clean architecture principles where domain exceptions are defined
at the application layer.
"""


class ResultsUploadError(Exception):
    """
    Base exception for results upload operations.

    All results upload-related exceptions inherit from this base class,
    allowing callers to catch all upload errors with a single except clause.
    """

    pass


class InvalidResultsDirectoryError(ResultsUploadError):
    """
    Raised when results directory is invalid or empty.

    Examples:
    - Directory does not exist
    - Path is not a directory
    - Directory contains no FRED output (no RUN* subdirectories)
    - Directory is not readable
    """

    pass


class ResultsPackagingError(ResultsUploadError):
    """
    Raised when ZIP file creation fails.

    Examples:
    - I/O error during ZIP creation
    - Insufficient disk space
    - File permissions error
    """

    pass


class ResultsStorageError(ResultsUploadError):
    """
    Raised when S3 upload fails.

    This exception should always contain sanitized error messages with
    AWS credentials removed for security.

    Attributes:
        sanitized: Flag indicating if AWS credentials were removed from message
    """

    def __init__(self, message: str, sanitized: bool = True):
        """
        Initialize storage error.

        Args:
            message: Error description (should be sanitized if containing AWS errors)
            sanitized: True if credentials have been removed from message
        """
        super().__init__(message)
        self.sanitized = sanitized


class ResultsMetadataError(ResultsUploadError):
    """
    Raised when database update fails after successful S3 upload.

    This represents a critical error condition where the ZIP file was successfully
    uploaded to S3, but the database update to record the results_url failed.
    This results in an orphaned S3 file.

    The orphaned_s3_url attribute allows operators to identify and clean up
    orphaned files, or implement compensation logic.

    Attributes:
        orphaned_s3_url: S3 URL of the orphaned results file
    """

    def __init__(self, message: str, orphaned_s3_url: str):
        """
        Initialize metadata error with orphaned file information.

        Args:
            message: Error description
            orphaned_s3_url: S3 URL of the successfully uploaded but orphaned file
        """
        super().__init__(message)
        self.orphaned_s3_url = orphaned_s3_url

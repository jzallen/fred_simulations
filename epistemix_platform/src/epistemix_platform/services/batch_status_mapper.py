"""
AWS Batch status mapping to RunStatus.

CRITICAL for epx alignment: Only set DONE when results are uploaded to S3.
This ensures epx can always retrieve results when status == DONE.
"""

from epistemix_platform.models.run import RunStatus


def map_batch_status_to_run_status(
    batch_status: str,
    results_uploaded: bool = False,
) -> RunStatus:
    """Map AWS Batch state to RunStatus with epx alignment.

    CRITICAL for epx: Only set DONE when results are uploaded to S3.
    This ensures epx can always retrieve results when status == DONE.

    Two-phase completion pattern:
    1. Batch job succeeds → Status stays RUNNING
    2. Results uploaded to S3 → Status changes to DONE

    Args:
        batch_status: AWS Batch job status
        results_uploaded: Whether results have been uploaded to S3

    Returns:
        RunStatus enum value

    Examples:
        >>> map_batch_status_to_run_status("SUCCEEDED", results_uploaded=True)
        RunStatus.DONE

        >>> map_batch_status_to_run_status("SUCCEEDED", results_uploaded=False)
        RunStatus.RUNNING

        >>> map_batch_status_to_run_status("FAILED")
        RunStatus.ERROR

        >>> map_batch_status_to_run_status("SUBMITTED")
        RunStatus.QUEUED
    """
    if batch_status == "SUCCEEDED":
        # Two-phase completion: DONE only after results uploaded
        return RunStatus.DONE if results_uploaded else RunStatus.RUNNING

    elif batch_status == "FAILED":
        return RunStatus.ERROR

    elif batch_status in ("SUBMITTED", "PENDING", "RUNNABLE"):
        return RunStatus.QUEUED

    elif batch_status in ("STARTING", "RUNNING"):
        return RunStatus.RUNNING

    else:
        # Unknown state - default to ERROR for safety
        return RunStatus.ERROR

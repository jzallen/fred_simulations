from epistemix_platform.models.job_s3_prefix import JobS3Prefix
from epistemix_platform.models.run_results import RunResults
from epistemix_platform.repositories.interfaces import (
    IJobRepository,
    IResultsRepository,
    IRunRepository,
)


def get_run_results(
    job_id: int,
    job_repository: IJobRepository,
    run_repository: IRunRepository,
    results_repository: IResultsRepository,
    bucket_name: str,
    expiration_seconds: int = 86400,  # 24 hours
) -> list[RunResults]:
    """
    Generate presigned download URLs for all runs in a job.

    This use case batch-generates presigned S3 URLs by reconstructing the S3 keys
    from job metadata (job.created_at) and run IDs, eliminating the need for
    persisted results_url fields.

    Args:
        job_id: ID of the job
        job_repository: Repository for fetching job metadata
        run_repository: Repository for fetching runs
        results_repository: Repository for generating presigned URLs
        bucket_name: S3 bucket name for results
        expiration_seconds: URL expiration time (default 24 hours)

    Returns:
        List of RunResults with presigned URLs for each run

    Raises:
        ValueError: If job not found

    Business Rules:
        - Generate URLs for ALL runs (results_url no longer required)
        - Reconstruct S3 key from job.created_at + run_id
        - Use 24-hour expiration for epx client compatibility
        - Return empty list if no runs exist
    """
    # Step 1: Fetch job to get created_at for S3 prefix
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    # Step 2: Create S3 prefix from job.created_at
    s3_prefix = JobS3Prefix.from_job(job)

    # Step 3: Fetch all runs for this job
    runs = run_repository.find_by_job_id(job_id)

    # Step 4: Generate presigned URL for each run
    results = []
    for run in runs:
        # Reconstruct S3 URL from prefix + run_id
        object_key = s3_prefix.run_results_key(run.id)
        results_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"

        # Generate presigned URL
        upload_location = results_repository.get_download_url(
            results_url=results_url,
            expiration_seconds=expiration_seconds,
        )

        results.append(RunResults(run_id=run.id, url=upload_location.url))

    return results

"""
Get job uploads use case for the Epistemix API.
This module retrieves and reads all upload contents associated with a job.
"""

from typing import List, Optional
import logging
from dataclasses import dataclass
from returns.pipeline import is_successful

from epistemix_api.repositories.interfaces import IJobRepository, IRunRepository
from epistemix_api.use_cases.read_upload_content import ReadUploadContent


logger = logging.getLogger(__name__)


@dataclass
class JobUpload:
    """Represents an upload associated with a job or run."""
    upload_type: str  # "job_config", "job_input", "run_output", etc.
    job_id: int
    run_id: Optional[int]
    s3_key: str
    content: Optional[str] = None
    error: Optional[str] = None


def get_job_uploads(
    job_repository: IJobRepository,
    run_repository: IRunRepository,
    job_id: int,
    bucket_name: str,
    region_name: Optional[str] = None
) -> List[JobUpload]:
    """
    Get all uploads associated with a job and its runs.
    
    This use case retrieves all upload locations for a job (config, input)
    and its associated runs, then reads the content from S3.
    
    Args:
        job_repository: Repository for job persistence
        run_repository: Repository for run persistence
        job_id: ID of the job to get uploads for
        bucket_name: S3 bucket name where uploads are stored
        region_name: AWS region name (optional)
        
    Returns:
        List of JobUpload objects with content or error messages
        
    Raises:
        ValueError: If job doesn't exist
    """
    # Check if job exists
    job = job_repository.find_by_id(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    
    uploads = []
    
    # Initialize the S3 content reader
    content_reader = ReadUploadContent(bucket_name=bucket_name, region_name=region_name)
    
    # Check for persisted job URLs
    if job.input_location:
        s3_key = _extract_s3_key_from_url(job.input_location, bucket_name)
        if s3_key:
            upload = JobUpload(
                upload_type="job_input",
                job_id=job_id,
                run_id=None,
                s3_key=s3_key
            )
            
            result = content_reader.execute(s3_key)
            if is_successful(result):
                upload.content = result.unwrap()
                logger.info(f"Found job_input for job {job_id} at {s3_key}")
            else:
                upload.error = result.failure()
                logger.warning(f"Could not retrieve job_input for job {job_id} at {s3_key}")
            uploads.append(upload)
    
    if job.config_location:
        s3_key = _extract_s3_key_from_url(job.config_location, bucket_name)
        if s3_key:
            upload = JobUpload(
                upload_type="job_config",
                job_id=job_id,
                run_id=None,
                s3_key=s3_key
            )
            
            result = content_reader.execute(s3_key)
            if is_successful(result):
                upload.content = result.unwrap()
                logger.info(f"Found job_config for job {job_id} at {s3_key}")
            else:
                upload.error = result.failure()
                logger.warning(f"Could not retrieve job_config for job {job_id} at {s3_key}")
            uploads.append(upload)
    
    # Get runs for the job
    runs = run_repository.find_by_job_id(job_id)
    logger.info(f"Found {len(runs)} runs for job {job_id}")
    
    # Add run-related uploads
    for run in runs:
        # Check if run has a URL stored
        if hasattr(run, 'url') and run.url:
            # Extract S3 key from URL if it's an S3 URL
            s3_key = _extract_s3_key_from_url(run.url, bucket_name)
            if s3_key:
                # Always use the key without run_id since that's the actual naming convention
                # Remove the _run_{id}_ part if it exists
                if f"_run_{run.id}_" in s3_key:
                    s3_key = s3_key.replace(f"_run_{run.id}_", "_")
                    logger.debug(f"Normalized S3 key to: {s3_key}")
                
                upload = JobUpload(
                    upload_type="run_output",
                    job_id=job_id,
                    run_id=run.id,
                    s3_key=s3_key
                )
                
                result = content_reader.execute(s3_key)
                if is_successful(result):
                    upload.content = result.unwrap()
                    logger.info(f"Found run output for run {run.id} at {s3_key}")
                else:
                    upload.error = result.failure()
                    logger.warning(f"Could not retrieve run output for run {run.id} at {s3_key}")
                
                uploads.append(upload)
        
        # Also try standard run output patterns
        run_patterns = [
            (f"run_{run.id}_output", f"run_{run.id}_output"),
            (f"run_{run.id}_results", f"run_{run.id}_results"),
            (f"run_{run.id}_logs", f"run_{run.id}_logs"),
        ]
        
        for upload_type, s3_key_pattern in run_patterns:
            possible_keys = [
                s3_key_pattern,
                f"{s3_key_pattern}.json",
                f"{s3_key_pattern}.txt",
                f"{s3_key_pattern}.log",
            ]
            
            for s3_key in possible_keys:
                upload = JobUpload(
                    upload_type=upload_type,
                    job_id=job_id,
                    run_id=run.id,
                    s3_key=s3_key
                )
                
                result = content_reader.execute(s3_key)
                if is_successful(result):
                    upload.content = result.unwrap()
                    uploads.append(upload)
                    logger.info(f"Found {upload_type} for run {run.id} at {s3_key}")
                    break
    
    return uploads


def _extract_s3_key_from_url(url: str, bucket_name: str) -> Optional[str]:
    """
    Extract S3 key from a URL.
    
    Args:
        url: The URL to parse
        bucket_name: The S3 bucket name
        
    Returns:
        The S3 key if extractable, None otherwise
    """
    if not url:
        return None
    
    # Remove query parameters (AWS signature, etc.)
    if '?' in url:
        url = url.split('?')[0]
    
    # Handle different URL formats
    if url.startswith(f"s3://{bucket_name}/"):
        return url[len(f"s3://{bucket_name}/"):]
    elif f"{bucket_name}.s3.amazonaws.com/" in url:
        parts = url.split(f"{bucket_name}.s3.amazonaws.com/")
        if len(parts) > 1:
            return parts[1]
    elif f"s3.amazonaws.com/{bucket_name}/" in url:
        parts = url.split(f"s3.amazonaws.com/{bucket_name}/")
        if len(parts) > 1:
            return parts[1]
    
    return None
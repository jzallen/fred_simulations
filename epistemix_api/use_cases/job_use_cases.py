"""
Job-related use cases for the Epistemix API.
These functions implement the core business logic for job operations.
"""

from typing import List
import logging

from ..models.job import Job, JobTag
from ..repositories.interfaces import IJobRepository


logger = logging.getLogger(__name__)


def register_job(
    job_repository: IJobRepository,
    user_id: int,
    tags: List[str] = None
) -> Job:
    """
    Register a new job for a user.
    
    This use case implements the core business logic for job registration.
    It validates business rules, creates an unpersisted job entity,
    and delegates persistence (including ID assignment) to the repository.
    
    Args:
        job_repository: Repository for job persistence
        user_id: ID of the user registering the job
        tags: Optional list of tags for the job
        
    Returns:
        The created and persisted Job entity with assigned ID
        
    Raises:
        ValueError: If user_id is invalid or business rules are violated
    """
    # Input validation
    if user_id <= 0:
        raise ValueError("User ID must be positive")
    
    if tags is None:
        tags = []
    
    # Validate tags according to business rules
    validate_tags(tags)
    
    # Create the unpersisted job entity using domain factory method
    job = Job.create_new(user_id=user_id, tags=tags)
    
    # Persist the job (repository will assign ID)
    saved_job = job_repository.save(job)
    
    # Log the business event
    logger.info(f"Job {saved_job.id} created for user {user_id} with tags {tags}")
    
    return saved_job


def validate_tags(tags: List[str]) -> None:
    """
    Validate tags according to business rules.
    
    This function implements tag validation logic that can be reused 
    across multiple use cases.
    
    Args:
        tags: List of tags to validate
        
    Raises:
        ValueError: If any tag is invalid
    """
    if not tags:
        return
    
    # Get valid tag values from the domain model
    valid_tag_values = [tag.value for tag in JobTag]
    
    for tag in tags:
        # Basic validation
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError(f"Tag must be a non-empty string: {tag}")
        
        # Note: For now, we allow unknown tags but could enforce strict validation
        # This is a business decision that can be easily changed here
        # 
        # Strict validation would look like:
        # if tag not in valid_tag_values:
        #     raise ValueError(f"Invalid tag: {tag}. Valid tags are: {valid_tag_values}")
        
        # Optional: Log unknown tags for monitoring
        if tag not in valid_tag_values:
            logger.warning(f"Unknown tag used: {tag}. Known tags: {valid_tag_values}")


# Future use cases can be added here:
# - submit_job()
# - update_job_status()  
# - delete_job()
# - etc.

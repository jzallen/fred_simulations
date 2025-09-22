"""
Archive uploads use case for the Epistemix API.
This module handles archiving uploads for manual intervention or job lifecycle management.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IUploadLocationRepository

logger = logging.getLogger(__name__)


def archive_uploads(
    upload_repository: IUploadLocationRepository,
    upload_locations: List[UploadLocation],
    days_since_create: Optional[int] = None,
    hours_since_create: Optional[int] = None,
    dry_run: bool = False,
) -> List[UploadLocation]:
    """
    Archive a list of upload locations.

    This use case handles manual archival of uploads when lifecycle policies
    fail or for completed jobs. The repository will filter based on age threshold
    if specified.

    Args:
        upload_repository: Repository for managing upload locations
        upload_locations: List of UploadLocation objects to potentially archive
        days_since_create: Optional - only archive uploads older than specified days
        hours_since_create: Optional - only archive uploads older than specified hours
        dry_run: If True, only report what would be archived without making changes

    Returns:
        List of UploadLocation objects that were (or would be) archived.
        Returns empty list if no upload_locations are provided or if no uploads
        meet the age criteria for archival.
    """
    if not upload_locations:
        logger.info("No upload locations provided for archival")
        return []

    # Dedupe Locations while preserving order
    #   Ideally managed by the repository but this prevents unnecessary calls to S3
    #   and log noise from errors for locations that have already been archived
    upload_locations = list(dict.fromkeys(upload_locations))

    # Calculate age threshold if specified
    age_threshold = None
    if hours_since_create is not None:
        age_threshold = datetime.now() - timedelta(hours=hours_since_create)
        age_desc = f"older than {hours_since_create} hours"
    elif days_since_create is not None:
        age_threshold = datetime.now() - timedelta(days=days_since_create)
        age_desc = f"older than {days_since_create} days"
    else:
        age_desc = "all provided uploads"

    logger.info(
        f"{'DRY RUN: ' if dry_run else ''}Archiving {age_desc} "
        f"({len(upload_locations)} locations provided)"
    )

    if dry_run:
        # In dry run, the repository will return what would be archived
        # based on the age threshold without making changes
        logger.info("Dry run mode - checking what would be archived")
        locations_to_archive = (
            upload_repository.filter_by_age(upload_locations, age_threshold)
            if age_threshold
            else upload_locations
        )

        logger.info(f"Would archive {len(locations_to_archive)} uploads")
        for location in locations_to_archive:
            sanitized_url = location.get_sanitized_url()
            logger.debug(f"  Would archive: {sanitized_url}")

        return locations_to_archive

    # Archive the uploads (transition to Glacier)
    # The repository will handle batch processing and age filtering
    archived_locations = upload_repository.archive_uploads(
        upload_locations, age_threshold=age_threshold
    )

    logger.info(f"Successfully archived {len(archived_locations)} uploads")

    # Log archived locations with sanitized URLs
    for location in archived_locations:
        sanitized_url = location.get_sanitized_url()
        logger.debug(f"  Archived: {sanitized_url}")

    return archived_locations

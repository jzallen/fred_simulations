"""
Use case for reading uploaded content from storage.
This use case downloads and returns the contents of an uploaded file.
"""

import logging

from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.repositories.interfaces import IUploadLocationRepository


logger = logging.getLogger(__name__)


def read_upload_content(
    upload_location_repository: IUploadLocationRepository, location: UploadLocation
) -> UploadContent:
    """
    Read the contents of an uploaded file from storage.

    This use case delegates to the repository to handle the actual storage
    interaction, maintaining clean architecture separation.

    Args:
        upload_location_repository: Repository for handling upload locations
        location: The upload location containing the URL

    Returns:
        UploadContent domain model

    Raises:
        ValueError: If the content cannot be read
    """
    # Delegate to the repository to read the content
    content = upload_location_repository.read_content(location)
    sanitized_url = location.get_sanitized_url()
    logger.info(f"Successfully read content from location: {sanitized_url}")
    return content

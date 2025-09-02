"""
Write to local filesystem use case.

This use case handles writing UploadContent to a local file path,
handling both text and binary content appropriately.
"""

import logging
from pathlib import Path

from epistemix_platform.models.upload_content import ContentType, UploadContent

logger = logging.getLogger(__name__)


def write_to_local(file_path: Path, content: UploadContent, force: bool = False) -> None:
    """
    Write upload content to a local file.

    This use case handles writing different content types to the filesystem,
    automatically determining whether to write as text or binary based on
    the content type.

    Args:
        file_path: Path object indicating where to write the file
        content: UploadContent object containing the data to write
        force: If True, overwrite existing files. If False, raise error if file exists

    Raises:
        FileExistsError: If file exists and force=False
        ValueError: If content validation fails
        IOError: If write operation fails
    """
    if not isinstance(file_path, Path):
        raise ValueError(f"file_path must be a Path object, got {type(file_path)}")

    if not isinstance(content, UploadContent):
        raise ValueError(f"content must be an UploadContent object, got {type(content)}")

    # Check if file exists and handle based on force flag
    if file_path.exists() and not force:
        raise FileExistsError(f"File already exists: {file_path}. Use force=True to overwrite.")

    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Log if overwriting
    if file_path.exists():
        logger.info(f"Overwriting existing file: {file_path}")

    # Determine write mode based on content type
    if content.content_type == ContentType.ZIP_ARCHIVE:
        # For ZIP archives, the raw_content is base64 encoded binary data
        # Write as binary after decoding
        import base64

        try:
            binary_data = base64.b64decode(content.raw_content)
            file_path.write_bytes(binary_data)
            logger.info(f"Wrote ZIP archive to {file_path} ({len(binary_data)} bytes)")
        except Exception as e:
            raise IOError(f"Failed to write ZIP archive to {file_path}: {e}")

    elif content.content_type == ContentType.BINARY:
        # For binary content, raw_content is hex-encoded preview
        # This is typically just a preview, not full content
        # In practice, full binary content would need different handling
        logger.warning(f"Writing binary preview/hex data to {file_path} - may not be complete file")
        file_path.write_text(content.raw_content, encoding=content.encoding)

    else:
        # For TEXT and JSON content types, write as text
        try:
            file_path.write_text(content.raw_content, encoding=content.encoding)
            logger.info(
                f"Wrote {content.content_type.value} content to {file_path} "
                f"({content.get_size()} bytes)"
            )
        except Exception as e:
            raise IOError(
                f"Failed to write {content.content_type.value} content to {file_path}: {e}"
            )

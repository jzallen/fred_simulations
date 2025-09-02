"""
Write to local filesystem use case.

This use case handles writing UploadContent to a local file path,
handling both text and binary content appropriately.
"""

import base64
import binascii
import logging
from pathlib import Path

from epistemix_platform.models.upload_content import ContentType, UploadContent

logger = logging.getLogger(__name__)


def _validate_base64(content: str) -> bool:
    """
    Validate that a string is valid base64 content.
    
    Args:
        content: String to validate
        
    Returns:
        True if valid base64, False otherwise
    """
    if not content:
        return False
        
    try:
        # Try to decode the base64 content
        base64.b64decode(content, validate=True)
        return True
    except (binascii.Error, ValueError):
        return False


def _validate_hex(content: str) -> bool:
    """
    Validate that a string is valid hexadecimal content.
    
    Args:
        content: String to validate
        
    Returns:
        True if valid hex, False otherwise
    """
    if not content:
        return False
        
    try:
        # Remove any whitespace and try to decode
        clean_content = content.replace(" ", "").replace("\n", "")
        bytes.fromhex(clean_content)
        return True
    except ValueError:
        return False


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
        # For ZIP archives, the raw_content should be base64 encoded binary data
        if not _validate_base64(content.raw_content):
            raise ValueError(
                f"ZIP archive content is not valid base64: content starts with "
                f"'{content.raw_content[:50]}...'"
            )
        
        try:
            binary_data = base64.b64decode(content.raw_content)
            file_path.write_bytes(binary_data)
            logger.info(f"Wrote ZIP archive to {file_path} ({len(binary_data)} bytes)")
        except Exception as e:
            raise IOError(f"Failed to write ZIP archive to {file_path}: {e}")

    elif content.content_type == ContentType.BINARY:
        # For binary content, raw_content should be hex-encoded data
        if content.encoding == "hex":
            # Validate and write hex-encoded content as binary
            if not _validate_hex(content.raw_content):
                raise ValueError(
                    f"Binary content is not valid hex: content starts with "
                    f"'{content.raw_content[:50]}...'"
                )
            
            try:
                # Remove whitespace and convert hex to bytes
                clean_hex = content.raw_content.replace(" ", "").replace("\n", "")
                binary_data = bytes.fromhex(clean_hex)
                file_path.write_bytes(binary_data)
                logger.info(f"Wrote binary content to {file_path} ({len(binary_data)} bytes)")
            except ValueError as e:
                raise ValueError(f"Failed to decode hex content: {e}")
            except Exception as e:
                raise IOError(f"Failed to write binary content to {file_path}: {e}")
        else:
            # This is typically just a preview, not full content
            logger.warning(
                f"Writing binary preview data to {file_path} - may not be complete file. "
                f"Encoding: {content.encoding}"
            )
            try:
                file_path.write_text(content.raw_content, encoding=content.encoding)
            except Exception as e:
                raise IOError(f"Failed to write binary preview to {file_path}: {e}")

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

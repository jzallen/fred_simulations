"""
UploadContent domain model for the Epistemix API.
Contains the core business logic for upload content entities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ContentType(Enum):
    """Enumeration of content types."""

    TEXT = "text"
    JSON = "json"
    ZIP_ARCHIVE = "zip_archive"
    BINARY = "binary"


@dataclass
class ZipFileEntry:
    """Represents a file entry within a ZIP archive."""

    name: str
    size: int
    compressed_size: int
    preview: Optional[str] = None  # Preview for text files

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        result = {"name": self.name, "size": self.size, "compressedSize": self.compressed_size}
        if self.preview:
            result["preview"] = self.preview
        return result


@dataclass
class UploadContent:
    """
    Domain entity representing the content of an uploaded file.

    This entity encapsulates the actual content read from an upload location,
    abstracting away the storage implementation details.
    """

    content_type: ContentType
    raw_content: str  # Text representation of the content
    encoding: str = "utf-8"
    zip_entries: Optional[List[ZipFileEntry]] = None  # For ZIP archives

    def __post_init__(self):
        """Post-initialization validation."""
        self._validate()

    def _validate(self):
        """Validate the content entity."""
        if not self.raw_content:
            raise ValueError("Content cannot be empty")

        if self.content_type == ContentType.ZIP_ARCHIVE and not self.zip_entries:
            raise ValueError("ZIP archive must have entries")

        if self.content_type != ContentType.ZIP_ARCHIVE and self.zip_entries:
            raise ValueError("Only ZIP archives can have zip_entries")

    def is_text(self) -> bool:
        """Check if content is text-based."""
        return self.content_type in [ContentType.TEXT, ContentType.JSON]

    def is_archive(self) -> bool:
        """Check if content is an archive."""
        return self.content_type == ContentType.ZIP_ARCHIVE

    def get_size(self) -> int:
        """Get the size of the content in bytes."""
        return len(self.raw_content.encode(self.encoding))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the content to a dictionary for API responses."""
        result = {
            "contentType": self.content_type.value,
            "content": self.raw_content,
            "encoding": self.encoding,
            "size": self.get_size(),
        }

        if self.zip_entries:
            result["zipEntries"] = [entry.to_dict() for entry in self.zip_entries]
            result["fileCount"] = len(self.zip_entries)

        return result

    @classmethod
    def create_text(cls, content: str, encoding: str = "utf-8") -> "UploadContent":
        """Factory method for creating text content."""
        return cls(content_type=ContentType.TEXT, raw_content=content, encoding=encoding)

    @classmethod
    def create_json(cls, content: str) -> "UploadContent":
        """Factory method for creating JSON content."""
        return cls(content_type=ContentType.JSON, raw_content=content, encoding="utf-8")

    @classmethod
    def create_zip_archive(
        cls, content_summary: str, entries: List[ZipFileEntry]
    ) -> "UploadContent":
        """Factory method for creating ZIP archive content."""
        return cls(
            content_type=ContentType.ZIP_ARCHIVE,
            raw_content=content_summary,
            encoding="utf-8",
            zip_entries=entries,
        )

    @classmethod
    def create_binary(cls, hex_preview: str) -> "UploadContent":
        """Factory method for creating binary content representation."""
        return cls(content_type=ContentType.BINARY, raw_content=hex_preview, encoding="hex")

    def __repr__(self) -> str:
        size_str = f", {self.get_size()} bytes"
        entries_str = f", {len(self.zip_entries)} files" if self.zip_entries else ""
        return f"UploadContent(type={self.content_type.value}{size_str}{entries_str})"

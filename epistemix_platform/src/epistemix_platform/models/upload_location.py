"""
Upload location domain model for the Epistemix API.
Contains the unified model for handling presigned URLs for various upload scenarios.
"""

from dataclasses import dataclass, field


@dataclass(slots=True)
class UploadLocation:
    """
    Represents a location for uploading content.

    This unified model replaces JobInputLocation, JobConfigLocation, and RunConfigLocation
    to provide a consistent interface for handling presigned URLs across different upload scenarios.
    """

    url: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary representation."""
        return {"url": self.url}

    def to_sanitized_dict(self) -> dict[str, str]:
        """Convert to dictionary representation with sanitized URL as the url value."""
        return {"url": self.get_sanitized_url()}

    def __eq__(self, other) -> bool:
        """Check equality based on URL."""
        if not isinstance(other, UploadLocation):
            return False
        return self.url == other.url

    def __hash__(self):
        return hash(self.url)

    def __repr__(self):
        """String representation for debugging."""
        return f"UploadLocation(url={self.url})"

    def extract_filename(self) -> str | None:
        """
        Extract filename from the URL.

        TODO: Consider generalizing this for non-S3 storage backends in the future.
        Currently assumes S3-style URLs and HTTP presigned URLs.

        Returns:
            Filename if found, None otherwise
        """
        if not self.url:
            return None

        # Remove query parameters
        url_without_params = self.url.split("?")[0]

        # Extract last component of path
        path_parts = url_without_params.split("/")
        if path_parts:
            filename = path_parts[-1]
            # Ensure it looks like a filename (has an extension)
            if filename and "." in filename:
                return filename

        return None

    def get_sanitized_url(self) -> str:
        """
        Get a sanitized version of the URL with sensitive parts masked.

        TODO: Consider generalizing this for non-S3 storage backends in the future.
        Currently handles S3 URLs and HTTP presigned URLs specifically.

        Returns:
            Sanitized URL string
        """
        if not self.url:
            return ""

        # Handle S3 URLs
        if self.url.startswith("s3://"):
            parts = self.url[5:].split("/", 1)
            if len(parts) >= 1:
                bucket = parts[0]
                # Mask part of bucket name
                if len(bucket) > 4:
                    bucket = bucket[:2] + "***" + bucket[-2:]
                path = parts[1] if len(parts) > 1 else ""
                return f"s3://{bucket}/{path}"

        # Handle HTTP(S) presigned URLs
        elif self.url.startswith(("http://", "https://")):
            # Remove query parameters which contain sensitive signatures
            base_url = self.url.split("?")[0]
            # Add indicator that parameters were removed
            return base_url

        # For other URL types, return as-is
        return self.url

"""
Tests for UploadLocation sanitization functionality.
"""

import pytest
from epistemix_api.models.upload_location import UploadLocation


class TestUploadLocationSanitization:
    """Test the sanitization methods of UploadLocation."""
    
    def test_to_dict_returns_original_url(self):
        """Test that to_dict returns the original URL unchanged."""
        url = "https://s3.amazonaws.com/mybucket/file.txt?X-Amz-Signature=secret123"
        location = UploadLocation(url=url)
        
        result = location.to_dict()
        
        assert result == {"url": url}
    
    def test_to_sanitized_dict_removes_query_params(self):
        """Test that to_sanitized_dict removes query parameters from HTTP URLs."""
        url = "https://s3.amazonaws.com/mybucket/file.txt?X-Amz-Signature=secret123&X-Amz-Credential=AKIAIOSFODNN7EXAMPLE"
        location = UploadLocation(url=url)
        
        result = location.to_sanitized_dict()
        
        assert result == {"url": "https://s3.amazonaws.com/mybucket/file.txt?[parameters_removed]"}
    
    def test_to_sanitized_dict_masks_s3_bucket_name(self):
        """Test that to_sanitized_dict masks S3 bucket names."""
        url = "s3://my-bucket-name/path/to/file.txt"
        location = UploadLocation(url=url)
        
        result = location.to_sanitized_dict()
        
        assert result == {"url": "s3://my***me/path/to/file.txt"}
    
    def test_to_sanitized_dict_handles_short_bucket_names(self):
        """Test that to_sanitized_dict handles short S3 bucket names."""
        url = "s3://test/file.txt"
        location = UploadLocation(url=url)
        
        result = location.to_sanitized_dict()
        
        # Short bucket names are not masked
        assert result == {"url": "s3://test/file.txt"}
    
    def test_to_sanitized_dict_handles_http_without_params(self):
        """Test that to_sanitized_dict handles HTTP URLs without parameters."""
        url = "http://example.com/file.txt"
        location = UploadLocation(url=url)
        
        result = location.to_sanitized_dict()
        
        assert result == {"url": "http://example.com/file.txt?[parameters_removed]"}
    
    def test_to_sanitized_dict_handles_empty_url(self):
        """Test that to_sanitized_dict handles empty URLs."""
        location = UploadLocation(url="")
        
        result = location.to_sanitized_dict()
        
        assert result == {"url": ""}
    
    def test_to_sanitized_dict_handles_unknown_url_scheme(self):
        """Test that to_sanitized_dict returns unknown URL schemes as-is."""
        url = "ftp://example.com/file.txt"
        location = UploadLocation(url=url)
        
        result = location.to_sanitized_dict()
        
        assert result == {"url": "ftp://example.com/file.txt"}
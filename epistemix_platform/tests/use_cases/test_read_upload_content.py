from unittest.mock import Mock

import pytest

from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.models.upload_location import UploadLocation
from epistemix_platform.use_cases.read_upload_content import read_upload_content


class TestReadUploadContent:
    @pytest.fixture
    def upload_location_repository(self):
        return Mock()

    def test_read_upload_content__successful_read__returns_content(
        self, upload_location_repository
    ):
        # Arrange
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/test-file.txt")
        expected_content = UploadContent.create_text("Hello, World!")
        upload_location_repository.read_content.return_value = expected_content

        # Act
        content = read_upload_content(upload_location_repository, location)

        # Assert
        assert content == expected_content
        upload_location_repository.read_content.assert_called_once_with(location)

    def test_read_upload_content__json_content__returns_json_upload_content(
        self, upload_location_repository
    ):
        # Arrange
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/config.json")
        json_data = '{"key": "value", "number": 42}'
        expected_content = UploadContent.create_json(json_data)
        upload_location_repository.read_content.return_value = expected_content

        # Act
        content = read_upload_content(upload_location_repository, location)

        # Assert
        assert content.content_type.value == "json"
        assert content.raw_content == json_data

    def test_read_upload_content__binary_content__returns_binary_upload_content(
        self, upload_location_repository
    ):
        # Arrange
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/binary.dat")
        hex_preview = "[Binary content - hex representation]:\n000102030405..."
        expected_content = UploadContent.create_binary(hex_preview)
        upload_location_repository.read_content.return_value = expected_content

        # Act
        content = read_upload_content(upload_location_repository, location)

        # Assert
        assert content.content_type.value == "binary"
        assert content.raw_content == hex_preview

    def test_read_upload_content__repository_raises_error__propagates_exception(
        self, upload_location_repository
    ):
        # Arrange
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/missing.txt")
        upload_location_repository.read_content.side_effect = ValueError("S3 error: NoSuchKey")

        # Act & Assert
        with pytest.raises(ValueError, match="S3 error: NoSuchKey"):
            read_upload_content(upload_location_repository, location)

    def test_read_upload_content__delegates_to_repository(self, upload_location_repository):
        # Arrange
        location = UploadLocation(url="https://s3.amazonaws.com/bucket/file.txt")
        expected_content = UploadContent.create_text("content")
        upload_location_repository.read_content.return_value = expected_content

        # Act
        read_upload_content(upload_location_repository, location)

        # Assert
        # Verify that the repository method was called with the correct parameter
        upload_location_repository.read_content.assert_called_once_with(location)

    def test_read_upload_content__different_locations__calls_repository_correctly(
        self, upload_location_repository
    ):
        # Arrange
        location1 = UploadLocation(url="https://s3.amazonaws.com/bucket/file1.txt")
        location2 = UploadLocation(url="https://s3.amazonaws.com/bucket/file2.txt")

        content1 = UploadContent.create_text("content1")
        content2 = UploadContent.create_text("content2")

        upload_location_repository.read_content.side_effect = [content1, content2]

        # Act
        result1 = read_upload_content(upload_location_repository, location1)
        result2 = read_upload_content(upload_location_repository, location2)

        # Assert
        assert result1.raw_content == "content1"
        assert result2.raw_content == "content2"

        # Verify both calls were made correctly
        assert upload_location_repository.read_content.call_count == 2
        upload_location_repository.read_content.assert_any_call(location1)
        upload_location_repository.read_content.assert_any_call(location2)

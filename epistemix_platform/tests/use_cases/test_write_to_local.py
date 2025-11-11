import pytest

from epistemix_platform.models.upload_content import UploadContent
from epistemix_platform.use_cases.write_to_local import write_to_local


class TestWriteToLocal:
    def test_write_to_local__with_text_content__writes_file_successfully(self, tmp_path):
        file_path = tmp_path / "test.txt"
        content = UploadContent.create_text("Hello, World!")

        write_to_local(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == "Hello, World!"

    def test_write_to_local__with_json_content__writes_file_successfully(self, tmp_path):
        file_path = tmp_path / "test.json"
        json_content = '{"key": "value", "number": 42}'
        content = UploadContent.create_json(json_content)

        write_to_local(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == json_content

    def test_write_to_local__with_zip_archive_content__writes_binary_file_successfully(self, tmp_path):
        from epistemix_platform.models.upload_content import ZipFileEntry

        file_path = tmp_path / "test.zip"
        # Create a simple base64-encoded zip content
        # This is a minimal valid ZIP file structure
        zip_bytes = (
            b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )

        # Create a dummy zip entry to satisfy validation
        zip_entry = ZipFileEntry(name="dummy.txt", size=100, compressed_size=50)

        # Create UploadContent with binary data and summary
        content = UploadContent.create_zip_archive(
            binary_content=zip_bytes, entries=[zip_entry], summary="[ZIP Archive Contents - 1 file]"
        )

        write_to_local(file_path, content)

        assert file_path.exists()
        assert file_path.read_bytes() == zip_bytes

    def test_write_to_local__when_parent_directories_missing__creates_parent_directories(self, tmp_path):
        file_path = tmp_path / "nested" / "deep" / "test.txt"
        content = UploadContent.create_text("Nested content")

        write_to_local(file_path, content)

        assert file_path.exists()
        assert file_path.read_text() == "Nested content"

    def test_write_to_local__when_file_exists_and_force_true__overwrites_file(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Original content")

        content = UploadContent.create_text("New content")
        write_to_local(file_path, content, force=True)

        assert file_path.read_text() == "New content"

    def test_write_to_local__when_file_exists_and_force_false__raises_file_exists_error(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("Existing content")

        content = UploadContent.create_text("New content")

        with pytest.raises(FileExistsError) as exc_info:
            write_to_local(file_path, content, force=False)

        assert "File already exists" in str(exc_info.value)
        # Verify original content is unchanged
        assert file_path.read_text() == "Existing content"

    def test_write_to_local__when_invalid_file_path_type__raises_value_error(self, tmp_path):
        content = UploadContent.create_text("Test content")

        with pytest.raises(ValueError) as exc_info:
            write_to_local("/not/a/path/object", content)

        assert "file_path must be a Path object" in str(exc_info.value)

    def test_write_to_local__when_invalid_content_type__raises_value_error(self, tmp_path):
        file_path = tmp_path / "test.txt"

        with pytest.raises(ValueError) as exc_info:
            write_to_local(file_path, "not an UploadContent object")

        assert "content must be an UploadContent object" in str(exc_info.value)

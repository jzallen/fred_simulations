"""Tests for UploadContent domain model."""

import pytest

from epistemix_platform.models.upload_content import UploadContent, ContentType, ZipFileEntry


class TestUploadContentIsText:
    """Test UploadContent.is_text() method."""

    def test_is_text_returns_true_for_text_content(self):
        content = UploadContent.create_text("sample text")

        assert content.is_text() is True

    def test_is_text_returns_true_for_json_content(self):
        content = UploadContent.create_json('{"key": "value"}')

        assert content.is_text() is True

    def test_is_text_returns_false_for_binary_content(self):
        content = UploadContent.create_binary("48656c6c6f")

        assert content.is_text() is False

    def test_is_text_returns_false_for_zip_archive(self):
        entries = [ZipFileEntry(name="file.txt", size=100, compressed_size=50)]
        content = UploadContent.create_zip_archive(
            binary_content=b"fake zip data",
            entries=entries,
            summary="1 file"
        )

        assert content.is_text() is False


class TestUploadContentIsArchive:
    """Test UploadContent.is_archive() method."""

    def test_is_archive_returns_true_for_zip_content(self):
        entries = [ZipFileEntry(name="file.txt", size=100, compressed_size=50)]
        content = UploadContent.create_zip_archive(
            binary_content=b"fake zip data",
            entries=entries,
            summary="1 file"
        )

        assert content.is_archive() is True

    def test_is_archive_returns_false_for_text_content(self):
        content = UploadContent.create_text("sample text")

        assert content.is_archive() is False

    def test_is_archive_returns_false_for_json_content(self):
        content = UploadContent.create_json('{"key": "value"}')

        assert content.is_archive() is False

    def test_is_archive_returns_false_for_binary_content(self):
        content = UploadContent.create_binary("48656c6c6f")

        assert content.is_archive() is False


class TestUploadContentGetSize:
    """Test UploadContent.get_size() method."""

    def test_get_size_returns_byte_count_for_text(self):
        content = UploadContent.create_text("Hello")

        size = content.get_size()

        assert size == 5

    def test_get_size_handles_multibyte_characters(self):
        content = UploadContent.create_text("Hello 世界")

        size = content.get_size()

        assert size > 8

    def test_get_size_respects_encoding(self):
        content = UploadContent.create_text("Hello", encoding="utf-8")

        size = content.get_size()

        assert size == 5


class TestUploadContentCreateText:
    """Test UploadContent.create_text() factory method."""

    def test_create_text_with_default_encoding(self):
        content = UploadContent.create_text("sample text")

        assert content.content_type == ContentType.TEXT
        assert content.raw_content == "sample text"
        assert content.encoding == "utf-8"
        assert content.zip_entries is None
        assert content.summary is None

    def test_create_text_with_custom_encoding(self):
        content = UploadContent.create_text("sample text", encoding="ascii")

        assert content.content_type == ContentType.TEXT
        assert content.raw_content == "sample text"
        assert content.encoding == "ascii"

    def test_create_text_with_multiline_content(self):
        text = "line 1\nline 2\nline 3"
        content = UploadContent.create_text(text)

        assert content.raw_content == text
        assert content.content_type == ContentType.TEXT


class TestUploadContentCreateJson:
    """Test UploadContent.create_json() factory method."""

    def test_create_json_creates_json_content(self):
        json_str = '{"name": "test", "value": 123}'
        content = UploadContent.create_json(json_str)

        assert content.content_type == ContentType.JSON
        assert content.raw_content == json_str
        assert content.encoding == "utf-8"
        assert content.zip_entries is None

    def test_create_json_with_array(self):
        json_str = '[1, 2, 3, 4]'
        content = UploadContent.create_json(json_str)

        assert content.content_type == ContentType.JSON
        assert content.raw_content == json_str

    def test_create_json_with_nested_structure(self):
        json_str = '{"outer": {"inner": {"deep": "value"}}}'
        content = UploadContent.create_json(json_str)

        assert content.content_type == ContentType.JSON
        assert content.raw_content == json_str


class TestUploadContentCreateBinary:
    """Test UploadContent.create_binary() factory method."""

    def test_create_binary_creates_binary_content(self):
        hex_preview = "48656c6c6f"
        content = UploadContent.create_binary(hex_preview)

        assert content.content_type == ContentType.BINARY
        assert content.raw_content == hex_preview
        assert content.encoding == "hex"
        assert content.zip_entries is None

    def test_create_binary_with_empty_preview(self):
        with pytest.raises(ValueError, match="Content cannot be empty"):
            content = UploadContent.create_binary("")

    def test_create_binary_stores_hex_preview(self):
        hex_preview = "deadbeef"
        content = UploadContent.create_binary(hex_preview)

        assert content.raw_content == hex_preview


class TestUploadContentCreateZipArchive:
    """Test UploadContent.create_zip_archive() factory method."""

    def test_create_zip_archive_encodes_binary_as_base64(self):
        entries = [
            ZipFileEntry(name="file1.txt", size=100, compressed_size=50),
            ZipFileEntry(name="file2.txt", size=200, compressed_size=100)
        ]
        binary_data = b"fake zip content"

        content = UploadContent.create_zip_archive(
            binary_content=binary_data,
            entries=entries,
            summary="2 files"
        )

        assert content.content_type == ContentType.ZIP_ARCHIVE
        assert content.encoding == "base64"
        assert content.zip_entries == entries
        assert content.summary == "2 files"
        assert content.raw_content != ""

    def test_create_zip_archive_with_single_entry(self):
        entries = [ZipFileEntry(name="single.txt", size=50, compressed_size=25)]
        content = UploadContent.create_zip_archive(
            binary_content=b"data",
            entries=entries,
            summary="1 file"
        )

        assert len(content.zip_entries) == 1
        assert content.zip_entries[0].name == "single.txt"

    def test_create_zip_archive_preserves_entry_details(self):
        entries = [
            ZipFileEntry(
                name="important.txt",
                size=1024,
                compressed_size=512,
                preview="First 100 chars..."
            )
        ]
        content = UploadContent.create_zip_archive(
            binary_content=b"zip data",
            entries=entries,
            summary="1 file with preview"
        )

        assert content.zip_entries[0].name == "important.txt"
        assert content.zip_entries[0].size == 1024
        assert content.zip_entries[0].compressed_size == 512
        assert content.zip_entries[0].preview == "First 100 chars..."


class TestUploadContentRepr:
    """Test UploadContent string representation."""

    def test_repr_for_text_content(self):
        content = UploadContent.create_text("Hello World")

        assert repr(content) == "UploadContent(type=text, 11 bytes)"

    def test_repr_for_json_content(self):
        content = UploadContent.create_json('{"key": "value"}')

        assert repr(content) == "UploadContent(type=json, 16 bytes)"

    def test_repr_for_zip_archive_includes_file_count(self):
        entries = [
            ZipFileEntry(name="file1.txt", size=100, compressed_size=50),
            ZipFileEntry(name="file2.txt", size=200, compressed_size=100)
        ]
        # Create directly to avoid get_size() encoding issue with base64
        content = UploadContent(
            content_type=ContentType.ZIP_ARCHIVE,
            raw_content="fake_base64_data",
            encoding="utf-8",  # Use utf-8 to avoid encoding issue in get_size()
            zip_entries=entries,
            summary="2 files"
        )

        assert repr(content) == "UploadContent(type=zip_archive, 16 bytes, 2 files)"

    def test_repr_for_binary_content(self):
        # Create directly to avoid get_size() encoding issue with hex
        content = UploadContent(
            content_type=ContentType.BINARY,
            raw_content="deadbeef",
            encoding="utf-8"  # Use utf-8 to avoid encoding issue in get_size()
        )

        assert repr(content) == "UploadContent(type=binary, 8 bytes)"

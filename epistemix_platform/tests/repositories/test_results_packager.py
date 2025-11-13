"""
Unit tests for FredResultsPackager service.

These tests verify the FRED results packaging service behavior using
behavioral specifications (Gherkin-style).

Behavioral Specifications:
==========================

Scenario 1: Successfully package a single RUN* directory
  Given a directory named "RUN4" containing simulation output files
  When I call package_directory with the RUN4 path
  Then a PackagedResults object is returned
  And the ZIP contains all files with "RUN4/" prefix
  And file_count matches the number of files
  And total_size_bytes equals the ZIP size
  And directory_name is "RUN4"

Scenario 2: Successfully package parent directory with multiple RUN* subdirectories
  Given a directory "output" containing "RUN1", "RUN2", "RUN3" subdirectories
  And each RUN* subdirectory contains simulation files
  When I call package_directory with the "output" path
  Then a PackagedResults object is returned
  And the ZIP contains files from all RUN* directories
  And file paths preserve the RUN*/file.txt structure
  And directory_name is "output"

Scenario 3: Reject non-existent directory
  Given a path that does not exist
  When I call package_directory with the non-existent path
  Then an InvalidResultsDirectoryError is raised
  And the error message indicates the directory does not exist

Scenario 4: Reject file path (not a directory)
  Given a path that points to a file (not a directory)
  When I call package_directory with the file path
  Then an InvalidResultsDirectoryError is raised
  And the error message indicates the path is not a directory

Scenario 5: Reject empty directory (no RUN* subdirectories)
  Given an empty directory with no RUN* subdirectories
  When I call package_directory with the empty directory
  Then an InvalidResultsDirectoryError is raised
  And the error message indicates no FRED output directories found

Scenario 6: Reject directory with no files
  Given a RUN4 directory that exists but contains no files
  When I call package_directory with the RUN4 path
  Then a PackagedResults object is returned
  And file_count is 0
  And the ZIP is empty but valid

Scenario 7: Handle ZIP creation I/O error gracefully
  Given a results directory that triggers an I/O error during ZIP creation
  When I call package_directory
  Then a ResultsPackagingError is raised
  And the error message describes the ZIP creation failure

Scenario 8: Verify correct archive paths in ZIP structure
  Given a single RUN4 directory with files "data.txt" and "subdir/results.csv"
  When I package the directory
  Then the ZIP contains "RUN4/data.txt" and "RUN4/subdir/results.csv"
  And for a parent directory with RUN1/ and RUN2/
  Then the ZIP contains "RUN1/data.txt" and "RUN2/data.txt" (no extra prefix)
"""

import zipfile
from io import BytesIO

import pytest

from epistemix_platform.exceptions import (
    InvalidResultsDirectoryError,
    ResultsPackagingError,
)
from epistemix_platform.use_cases.upload_results import PackagedResults, _FredResultsPackager


class TestFredResultsPackager:
    """Test suite for _FredResultsPackager (internal implementation)."""

    @pytest.fixture
    def packager(self):
        """Create a _FredResultsPackager instance."""
        return _FredResultsPackager()

    @pytest.fixture
    def single_run_dir(self, tmp_path):
        """Create a single RUN4 directory with test files."""
        run_dir = tmp_path / "RUN4"
        run_dir.mkdir()

        # Create test files
        (run_dir / "data.txt").write_text("simulation data")
        (run_dir / "results.csv").write_text("time,value\n1,100\n2,200")

        # Create subdirectory with file
        subdir = run_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested file")

        return run_dir

    @pytest.fixture
    def parent_with_multiple_runs(self, tmp_path):
        """Create a parent directory with multiple RUN* subdirectories."""
        parent_dir = tmp_path / "output"
        parent_dir.mkdir()

        # Create RUN1
        run1 = parent_dir / "RUN1"
        run1.mkdir()
        (run1 / "data1.txt").write_text("run 1 data")
        (run1 / "results1.csv").write_text("time,value\n1,10")

        # Create RUN2
        run2 = parent_dir / "RUN2"
        run2.mkdir()
        (run2 / "data2.txt").write_text("run 2 data")

        # Create RUN3
        run3 = parent_dir / "RUN3"
        run3.mkdir()
        (run3 / "data3.txt").write_text("run 3 data")

        return parent_dir

    @pytest.fixture
    def empty_directory(self, tmp_path):
        """Create an empty directory with no RUN* subdirectories."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        return empty_dir

    @pytest.fixture
    def empty_run_dir(self, tmp_path):
        """Create a RUN directory with no files."""
        run_dir = tmp_path / "RUN5"
        run_dir.mkdir()
        return run_dir

    # ==========================================================================
    # Scenario 1: Successfully package a single RUN* directory
    # ==========================================================================

    def test_package_single_run_directory(self, packager, single_run_dir):
        """
        Given a directory named "RUN4" containing simulation output files
        When I call package_directory with the RUN4 path
        Then a PackagedResults object is returned
        And the ZIP contains all files with "RUN4/" prefix
        And file_count matches the number of files
        And total_size_bytes equals the ZIP size
        And directory_name is "RUN4"
        """
        # Act
        result = packager.package_directory(single_run_dir)

        # Assert
        assert isinstance(result, PackagedResults)
        assert result.file_count == 3  # data.txt, results.csv, subdir/nested.txt
        assert result.total_size_bytes == len(result.zip_content)
        assert result.directory_name == "RUN4"

        # Verify ZIP structure
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()
            assert "RUN4/data.txt" in names
            assert "RUN4/results.csv" in names
            assert "RUN4/subdir/nested.txt" in names

            # Verify content
            assert zf.read("RUN4/data.txt").decode() == "simulation data"

    # ==========================================================================
    # Scenario 2: Successfully package parent directory with multiple RUN* subdirectories
    # ==========================================================================

    def test_package_parent_with_multiple_runs(self, packager, parent_with_multiple_runs):
        """
        Given a directory "output" containing "RUN1", "RUN2", "RUN3" subdirectories
        And each RUN* subdirectory contains simulation files
        When I call package_directory with the "output" path
        Then a PackagedResults object is returned
        And the ZIP contains files from all RUN* directories
        And file paths preserve the RUN*/file.txt structure
        And directory_name is "output"
        """
        # Act
        result = packager.package_directory(parent_with_multiple_runs)

        # Assert
        assert isinstance(result, PackagedResults)
        assert result.file_count == 4  # data1.txt, results1.csv, data2.txt, data3.txt = 4 files
        assert result.directory_name == "output"

        # Verify ZIP structure
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()
            # Files should preserve RUN*/file structure (no extra "output/" prefix)
            assert "RUN1/data1.txt" in names
            assert "RUN1/results1.csv" in names
            assert "RUN2/data2.txt" in names
            assert "RUN3/data3.txt" in names

            # Verify content
            assert zf.read("RUN1/data1.txt").decode() == "run 1 data"

    # ==========================================================================
    # Scenario 3: Reject non-existent directory
    # ==========================================================================

    def test_reject_nonexistent_directory(self, packager, tmp_path):
        """
        Given a path that does not exist
        When I call package_directory with the non-existent path
        Then an InvalidResultsDirectoryError is raised
        And the error message indicates the directory does not exist
        """
        # Arrange
        nonexistent_path = tmp_path / "does_not_exist"

        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError) as exc_info:
            packager.package_directory(nonexistent_path)

        assert "does not exist" in str(exc_info.value).lower()

    # ==========================================================================
    # Scenario 4: Reject file path (not a directory)
    # ==========================================================================

    def test_reject_file_path(self, packager, tmp_path):
        """
        Given a path that points to a file (not a directory)
        When I call package_directory with the file path
        Then an InvalidResultsDirectoryError is raised
        And the error message indicates the path is not a directory
        """
        # Arrange
        file_path = tmp_path / "somefile.txt"
        file_path.write_text("not a directory")

        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError) as exc_info:
            packager.package_directory(file_path)

        assert "not a directory" in str(exc_info.value).lower()

    # ==========================================================================
    # Scenario 5: Reject empty directory (no RUN* subdirectories)
    # ==========================================================================

    def test_reject_empty_directory(self, packager, empty_directory):
        """
        Given an empty directory with no RUN* subdirectories
        When I call package_directory with the empty directory
        Then an InvalidResultsDirectoryError is raised
        And the error message indicates no FRED output directories found
        """
        # Act & Assert
        with pytest.raises(InvalidResultsDirectoryError) as exc_info:
            packager.package_directory(empty_directory)

        error_message = str(exc_info.value).lower()
        assert "no fred output directories" in error_message or "run" in error_message

    # ==========================================================================
    # Scenario 6: Reject directory with no files
    # ==========================================================================

    def test_package_empty_run_directory(self, packager, empty_run_dir):
        """
        Given a RUN4 directory that exists but contains no files
        When I call package_directory with the RUN4 path
        Then a PackagedResults object is returned
        And file_count is 0
        And the ZIP is empty but valid
        """
        # Act
        result = packager.package_directory(empty_run_dir)

        # Assert
        assert isinstance(result, PackagedResults)
        assert result.file_count == 0
        assert result.directory_name == "RUN5"

        # Verify ZIP is valid but empty
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            assert len(zf.namelist()) == 0

    # ==========================================================================
    # Scenario 7: Handle ZIP creation I/O error gracefully
    # ==========================================================================

    def test_handle_zip_creation_io_error(self, packager, single_run_dir, monkeypatch):
        """
        Given a results directory that triggers an I/O error during ZIP creation
        When I call package_directory
        Then a ResultsPackagingError is raised
        And the error message describes the ZIP creation failure
        """

        # Arrange: Mock zipfile.ZipFile to raise OSError
        def failing_zipfile():
            raise OSError("Disk full - cannot write ZIP")

        monkeypatch.setattr(zipfile, "ZipFile", failing_zipfile)

        # Act & Assert
        with pytest.raises(ResultsPackagingError) as exc_info:
            packager.package_directory(single_run_dir)

        assert "failed to create zip" in str(exc_info.value).lower()

    # ==========================================================================
    # Scenario 8: Verify correct archive paths in ZIP structure
    # ==========================================================================

    def test_verify_archive_paths_single_run(self, packager, single_run_dir):
        """
        Given a single RUN4 directory with files "data.txt" and "subdir/results.csv"
        When I package the directory
        Then the ZIP contains "RUN4/data.txt" and "RUN4/subdir/results.csv"
        """
        # Act
        result = packager.package_directory(single_run_dir)

        # Assert - verify archive paths include RUN4 prefix
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()
            assert "RUN4/data.txt" in names
            assert "RUN4/subdir/nested.txt" in names
            # Verify no files without RUN4 prefix
            assert not any(name for name in names if not name.startswith("RUN4/"))

    def test_verify_archive_paths_parent_directory(self, packager, parent_with_multiple_runs):
        """
        For a parent directory with RUN1/ and RUN2/
        Then the ZIP contains "RUN1/data.txt" and "RUN2/data.txt" (no extra prefix)
        """
        # Act
        result = packager.package_directory(parent_with_multiple_runs)

        # Assert - verify archive paths have no extra parent prefix
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()
            # Should be RUN1/file, not output/RUN1/file
            assert "RUN1/data1.txt" in names
            assert "RUN2/data2.txt" in names
            # Verify no files have "output/" prefix
            assert not any(name for name in names if name.startswith("output/"))

    # ==========================================================================
    # Scenario 9: Security - Prevent symlink escape attacks (CRITICAL)
    # ==========================================================================

    def test_prevent_symlink_escape_attack(self, packager, tmp_path):
        """
        Given a RUN directory with a symlink pointing outside the results tree
        When I package the directory
        Then the symlink target file is NOT included in the ZIP
        And only files within the RUN directory are packaged
        """
        # Arrange: Create a sensitive file outside the results directory
        sensitive_dir = tmp_path / "sensitive"
        sensitive_dir.mkdir()
        sensitive_file = sensitive_dir / "secrets.txt"
        sensitive_file.write_text("AWS_SECRET_KEY=super-secret-do-not-leak")

        # Create RUN directory with legitimate files
        run_dir = tmp_path / "RUN1"
        run_dir.mkdir()
        (run_dir / "legitimate.txt").write_text("safe data")

        # Create symlink inside RUN1 that points to sensitive file outside
        symlink_path = run_dir / "evil_symlink.txt"
        symlink_path.symlink_to(sensitive_file)

        # Act
        result = packager.package_directory(run_dir)

        # Assert: ZIP should NOT contain the symlink target content
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()

            # Should contain legitimate file
            assert "RUN1/legitimate.txt" in names

            # Should NOT contain symlink or its target content
            assert "RUN1/evil_symlink.txt" not in names
            assert "RUN1/secrets.txt" not in names

            # Verify the sensitive content is not in the ZIP
            for name in names:
                content = zf.read(name).decode()
                assert "AWS_SECRET_KEY" not in content
                assert "super-secret" not in content

    def test_prevent_non_run_directory_inclusion(self, packager, tmp_path):
        """
        Given a parent directory with RUN* subdirectories AND non-RUN directories
        When I package the parent directory
        Then only files from RUN* directories are included
        And files from non-RUN directories are excluded
        """
        # Arrange: Create parent with RUN and non-RUN directories
        parent_dir = tmp_path / "output"
        parent_dir.mkdir()

        # Create legitimate RUN directory
        run1 = parent_dir / "RUN1"
        run1.mkdir()
        (run1 / "data.txt").write_text("run 1 data")

        # Create non-RUN directory that should be EXCLUDED
        config_dir = parent_dir / "config"
        config_dir.mkdir()
        (config_dir / "sensitive_config.txt").write_text("DB_PASSWORD=secret123")

        # Create another non-RUN directory
        logs_dir = parent_dir / "logs"
        logs_dir.mkdir()
        (logs_dir / "error.log").write_text("ERROR: secret token xyz")

        # Act
        result = packager.package_directory(parent_dir)

        # Assert: Only RUN1 files should be in ZIP
        with zipfile.ZipFile(BytesIO(result.zip_content)) as zf:
            names = zf.namelist()

            # Should contain RUN1 files
            assert "RUN1/data.txt" in names

            # Should NOT contain non-RUN directory files
            assert "config/sensitive_config.txt" not in names
            assert "logs/error.log" not in names

            # Verify no sensitive content leaked
            for name in names:
                content = zf.read(name).decode()
                assert "DB_PASSWORD" not in content
                assert "secret token" not in content

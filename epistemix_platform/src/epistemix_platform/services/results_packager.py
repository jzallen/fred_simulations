"""
Results packager service for FRED simulation results.

This module provides services for packaging FRED simulation results into
ZIP files, handling the complexity of different directory structures and
validating results before packaging.
"""

import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from epistemix_platform.exceptions import (
    InvalidResultsDirectoryError,
    ResultsPackagingError,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PackagedResults:
    """
    Value object representing packaged simulation results.

    Immutable to ensure integrity - once created, content cannot change.
    This follows the value object pattern from Domain-Driven Design.

    Attributes:
        zip_content: Binary ZIP file content
        file_count: Number of files included in ZIP
        total_size_bytes: Total size of ZIP file in bytes
        directory_name: Name of the results directory (e.g., "RUN4")
    """

    zip_content: bytes
    file_count: int
    total_size_bytes: int
    directory_name: str


class IResultsPackager(Protocol):
    """
    Protocol (interface) for packaging FRED simulation results.

    This service abstracts file system operations and ZIP creation,
    allowing the use case layer to remain independent of implementation details.
    """

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package a FRED results directory into a ZIP file.

        Validates that:
        - Directory exists and is readable
        - Contains at least one RUN* subdirectory OR is itself a RUN* directory
        - Files can be zipped successfully

        Args:
            results_dir: Path to results directory

        Returns:
            PackagedResults value object with ZIP content and metadata

        Raises:
            InvalidResultsDirectoryError: If directory validation fails
            ResultsPackagingError: If ZIP creation fails
        """
        ...


class FredResultsPackager:
    """
    Concrete implementation for packaging FRED simulation results.

    This service handles the FRED-specific directory structure conventions:
    - Results can be in a single RUN* directory
    - Or in a parent directory containing multiple RUN* subdirectories

    The ZIP file preserves the directory structure for compatibility with
    FRED analysis tools.
    """

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package FRED results following current ZIP structure.

        The ZIP structure depends on input:
        - Single RUN4 directory: ZIP contains RUN4/file1.txt, RUN4/file2.txt
        - Parent with RUN1, RUN2: ZIP contains RUN1/..., RUN2/...

        Args:
            results_dir: Path to results directory

        Returns:
            PackagedResults with ZIP content and metadata

        Raises:
            InvalidResultsDirectoryError: If directory is invalid
            ResultsPackagingError: If ZIP creation fails
        """
        # Step 1: Validate directory exists
        self._validate_directory_exists(results_dir)

        # Step 2: Find RUN* directories
        run_dirs = self._find_run_directories(results_dir)
        is_single_run_dir = self._is_run_directory(results_dir)

        if not run_dirs and not is_single_run_dir:
            raise InvalidResultsDirectoryError(
                f"No FRED output directories (RUN*) found in {results_dir}. "
                "Expected either a RUN* directory or a parent containing RUN*/ subdirectories."
            )

        logger.info(
            "Found %s in %s",
            f"{len(run_dirs)} RUN directories" if run_dirs else f"single directory {results_dir.name}",
            results_dir,
        )

        # Step 3: Create ZIP in memory
        try:
            zip_content, file_count = self._create_zip(results_dir, run_dirs, is_single_run_dir)
        except Exception as e:
            raise ResultsPackagingError(f"Failed to create ZIP file: {e}") from e

        # Step 4: Get metadata
        total_size = len(zip_content)
        logger.info(f"Created ZIP file: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")

        return PackagedResults(
            zip_content=zip_content,
            file_count=file_count,
            total_size_bytes=total_size,
            directory_name=results_dir.name,
        )

    def _validate_directory_exists(self, results_dir: Path) -> None:
        """
        Validate that directory exists and is actually a directory.

        Args:
            results_dir: Path to validate

        Raises:
            InvalidResultsDirectoryError: If validation fails
        """
        if not results_dir.exists():
            raise InvalidResultsDirectoryError(f"Results directory does not exist: {results_dir}")

        if not results_dir.is_dir():
            raise InvalidResultsDirectoryError(f"Path is not a directory: {results_dir}")

    def _find_run_directories(self, path: Path) -> list[Path]:
        """
        Find all RUN* subdirectories in the given path.

        Args:
            path: Directory to search

        Returns:
            List of RUN* subdirectories
        """
        return [p for p in path.glob("RUN*") if p.is_dir()]

    def _is_run_directory(self, path: Path) -> bool:
        """
        Check if path itself is a RUN* directory.

        Args:
            path: Path to check

        Returns:
            True if path name starts with "RUN" (case-insensitive)
        """
        return path.name.upper().startswith("RUN") and path.is_dir()

    def _create_zip(
        self, results_dir: Path, run_dirs: list[Path], is_single_run: bool
    ) -> tuple[bytes, int]:
        """
        Create ZIP file from results directory.

        Args:
            results_dir: Root directory to zip
            run_dirs: List of RUN* subdirectories (if parent directory)
            is_single_run: True if results_dir itself is a RUN* directory

        Returns:
            Tuple of (zip_content_bytes, file_count)

        Raises:
            Exception: If ZIP creation fails (I/O error, permissions, etc.)
        """
        zip_buffer = io.BytesIO()
        file_count = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in results_dir.rglob("*"):
                if file_path.is_file():
                    arcname = self._calculate_archive_name(file_path, results_dir, run_dirs, is_single_run)
                    zip_file.write(file_path, arcname=arcname.as_posix())
                    file_count += 1
                    logger.debug(f"Added to ZIP: {arcname}")

        return zip_buffer.getvalue(), file_count

    def _calculate_archive_name(
        self, file_path: Path, results_dir: Path, run_dirs: list[Path], is_single_run: bool
    ) -> Path:
        """
        Calculate the archive path for a file in the ZIP.

        Logic:
        - Parent with multiple RUN* dirs: preserve relative path from parent
        - Single RUN* directory: prefix with RUN directory name

        Args:
            file_path: Path to file being added
            results_dir: Root results directory
            run_dirs: List of RUN* subdirectories
            is_single_run: True if results_dir is itself a RUN* directory

        Returns:
            Path to use as archive name in ZIP
        """
        if run_dirs:
            # Parent directory case: preserve relative path from results_dir
            # Example: results_dir=/output, file=/output/RUN1/data.txt -> RUN1/data.txt
            return file_path.relative_to(results_dir)
        else:
            # Single RUN* directory case: prefix with directory name
            # Example: results_dir=/output/RUN4, file=/output/RUN4/data.txt -> RUN4/data.txt
            return Path(results_dir.name) / file_path.relative_to(results_dir)

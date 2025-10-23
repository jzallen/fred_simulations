# Phase 3: Design Planning - Clean Architecture Blueprint

## Overview
This document provides the architectural design for the Phase 4 clean rebuild. It defines interfaces, responsibilities, and implementation strategy WITHOUT writing production code.

**Date:** 2025-10-23
**Branch:** `zallen/fred-31-add-epistemix-cli-command-to-upload-simulation-results-to-s3`
**Phase:** Phase 3 - Design Planning
**Status:** Design complete

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│ CLI Layer (epistemix-cli)                                            │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ jobs results upload command                                 │     │
│  │ - Parse arguments (job_id, run_id, results_dir)            │     │
│  │ - Build dependencies (repositories, services, controller)   │     │
│  │ - Call controller.upload_results()                          │     │
│  │ - Format output, handle ResultsUploadError                  │     │
│  └────────────────────────────────────────────────────────────┘     │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│ Use Case Layer                                                        │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │ upload_results() use case                                   │     │
│  │                                                             │     │
│  │ 1. Validate run exists and belongs to job                  │     │
│  │ 2. Package results directory → ZIP                          │     │
│  │ 3. Upload ZIP to S3                                         │     │
│  │ 4. Update run metadata (URL, timestamp, status)            │     │
│  │ 5. Handle failures with proper error types                 │     │
│  │                                                             │     │
│  │ Dependencies (injected via constructor):                    │     │
│  │   - IRunRepository                                          │     │
│  │   - IResultsPackager                                        │     │
│  │   - IResultsRepository                                      │     │
│  │   - ITimeProvider                                           │     │
│  └────────────────────────────────────────────────────────────┘     │
└────┬──────────┬──────────┬──────────┬───────────────────────────────┘
     │          │          │          │
┌────▼─────┐ ┌─▼────────┐ ┌▼────────┐ ┌▼──────────────────┐
│          │ │          │ │         │ │                   │
│ Results  │ │ Results  │ │  Run    │ │  Time Provider    │
│ Packager │ │Repository│ │Repository│ │  Service          │
│ Service  │ │ (S3)     │ │  (DB)   │ │                   │
│          │ │          │ │         │ │                   │
└──────────┘ └──────────┘ └─────────┘ └───────────────────┘
```

---

## Component Designs

### 1. IResultsPackager Interface

**Purpose:** Abstract file system operations and ZIP creation logic.

**Interface:**
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class PackagedResults:
    """
    Value object representing packaged simulation results.

    Immutable to ensure integrity - once created, content cannot change.
    """
    zip_content: bytes
    file_count: int
    total_size_bytes: int
    directory_name: str  # e.g., "RUN4" or parent directory name


class IResultsPackager(Protocol):
    """Service protocol for packaging FRED simulation results into ZIP files."""

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package a FRED results directory into a ZIP file.

        Validates that:
        - Directory exists and is readable
        - Contains at least one RUN* subdirectory OR is itself a RUN* directory
        - Files are not empty (optional validation)

        Args:
            results_dir: Path to results directory

        Returns:
            PackagedResults value object with ZIP content and metadata

        Raises:
            InvalidResultsDirectoryError: If directory validation fails
            ResultsPackagingError: If ZIP creation fails
        """
        ...
```

**Responsibilities:**
- ✅ Validate results directory structure
- ✅ Handle both single RUN* dir and parent with multiple RUN* dirs
- ✅ Create ZIP with proper archive structure
- ✅ Calculate metadata (file count, size)
- ✅ Return immutable value object

**Does NOT:**
- ❌ Know about S3 or storage
- ❌ Know about database or Run entities
- ❌ Handle upload or persistence

---

### 2. FredResultsPackager Implementation

**Implementation Strategy:**
```python
import zipfile
from pathlib import Path
from typing import List


class FredResultsPackager:
    """Concrete implementation for packaging FRED simulation results."""

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """Package FRED results following current ZIP structure."""

        # Step 1: Validate directory exists
        if not results_dir.exists():
            raise InvalidResultsDirectoryError(
                f"Results directory does not exist: {results_dir}"
            )

        if not results_dir.is_dir():
            raise InvalidResultsDirectoryError(
                f"Path is not a directory: {results_dir}"
            )

        # Step 2: Find RUN* directories
        run_dirs = self._find_run_directories(results_dir)
        is_single_run_dir = self._is_run_directory(results_dir)

        if not run_dirs and not is_single_run_dir:
            raise InvalidResultsDirectoryError(
                f"No FRED output directories (RUN*) found in {results_dir}. "
                "Expected either a RUN* directory or a parent containing RUN*/ subdirectories."
            )

        # Step 3: Create ZIP in memory
        zip_buffer = io.BytesIO()
        file_count = 0

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in results_dir.rglob("*"):
                if file_path.is_file():
                    arcname = self._calculate_archive_name(
                        file_path, results_dir, run_dirs, is_single_run_dir
                    )
                    zip_file.write(file_path, arcname=arcname.as_posix())
                    file_count += 1

        # Step 4: Get ZIP content and metadata
        zip_content = zip_buffer.getvalue()
        total_size = len(zip_content)

        return PackagedResults(
            zip_content=zip_content,
            file_count=file_count,
            total_size_bytes=total_size,
            directory_name=results_dir.name,
        )

    def _find_run_directories(self, path: Path) -> List[Path]:
        """Find all RUN* subdirectories."""
        return [p for p in path.glob("RUN*") if p.is_dir()]

    def _is_run_directory(self, path: Path) -> bool:
        """Check if path itself is a RUN* directory."""
        return path.name.upper().startswith("RUN") and path.is_dir()

    def _calculate_archive_name(
        self,
        file_path: Path,
        results_dir: Path,
        run_dirs: List[Path],
        is_single_run: bool
    ) -> Path:
        """Calculate the archive path for a file in the ZIP."""
        if run_dirs:
            # Parent directory case: preserve relative path
            return file_path.relative_to(results_dir)
        else:
            # Single RUN* directory case: prefix with directory name
            return Path(results_dir.name) / file_path.relative_to(results_dir)
```

**Testing Strategy:**
- Test with single RUN4 directory
- Test with parent containing RUN1, RUN2, RUN3
- Test with empty directory (should fail)
- Test with nonexistent directory (should fail)
- Verify ZIP structure matches expected format

---

### 3. IResultsRepository Interface (Already Exists)

**Current Interface:**
```python
@runtime_checkable
class IResultsRepository(Protocol):
    """Protocol for simulation results storage operations."""

    def upload_results(
        self,
        job_id: int,
        run_id: int,
        zip_content: bytes
    ) -> UploadLocation:
        """Upload results ZIP to S3 using IAM credentials."""
        ...

    def get_download_url(
        self,
        results_url: str,
        expiration_seconds: int = 3600
    ) -> UploadLocation:
        """Generate presigned GET URL for downloads."""
        ...
```

**Status:** ✅ Interface already defined in Phase 1

**Changes Needed:** None - interface is correct

---

### 4. S3ResultsRepository Implementation (NEW - Critical)

**Implementation Design:**
```python
import re
import boto3
from botocore.exceptions import ClientError
from epistemix_platform.models.upload_location import UploadLocation


class S3ResultsRepository:
    """
    S3-based repository for server-side simulation results uploads.

    Uses direct boto3.put_object() with IAM credentials, NOT presigned URLs.
    Implements credential sanitization for security.
    """

    def __init__(self, s3_client: boto3.client, bucket_name: str):
        """
        Initialize S3 results repository.

        Args:
            s3_client: Configured boto3 S3 client (with IAM credentials)
            bucket_name: S3 bucket name for results storage
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def upload_results(
        self,
        job_id: int,
        run_id: int,
        zip_content: bytes
    ) -> UploadLocation:
        """
        Upload simulation results ZIP to S3.

        S3 Key Format: results/job_{job_id}/run_{run_id}.zip
        Content-Type: application/zip

        Args:
            job_id: Job identifier
            run_id: Run identifier
            zip_content: Binary ZIP file content

        Returns:
            UploadLocation with S3 HTTPS URL

        Raises:
            ResultsStorageError: If S3 upload fails (with sanitized error message)
        """
        object_key = self._generate_results_key(job_id, run_id)

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=zip_content,
                ContentType="application/zip",
            )
        except ClientError as e:
            # CRITICAL: Sanitize credentials before logging/raising
            sanitized_message = self._sanitize_credentials(str(e))
            raise ResultsStorageError(
                f"Failed to upload results to S3: {sanitized_message}"
            ) from e

        # Generate S3 HTTPS URL (not presigned - permanent URL)
        results_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"

        return UploadLocation(url=results_url)

    def get_download_url(
        self,
        results_url: str,
        expiration_seconds: int = 3600
    ) -> UploadLocation:
        """
        Generate presigned GET URL for downloading results.

        Args:
            results_url: S3 URL of the results file
            expiration_seconds: URL validity period (default 1 hour)

        Returns:
            UploadLocation with presigned download URL

        Raises:
            ValueError: If results_url is invalid
            ResultsStorageError: If presigned URL generation fails
        """
        # Extract bucket and key from S3 URL
        object_key = self._extract_key_from_url(results_url)

        try:
            presigned_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                },
                ExpiresIn=expiration_seconds
            )
        except ClientError as e:
            sanitized_message = self._sanitize_credentials(str(e))
            raise ResultsStorageError(
                f"Failed to generate download URL: {sanitized_message}"
            ) from e

        return UploadLocation(url=presigned_url)

    def _generate_results_key(self, job_id: int, run_id: int) -> str:
        """Generate S3 object key for results ZIP."""
        return f"results/job_{job_id}/run_{run_id}.zip"

    def _extract_key_from_url(self, s3_url: str) -> str:
        """
        Extract object key from S3 URL.

        Supports formats:
        - https://bucket.s3.amazonaws.com/results/job_123/run_4.zip
        - s3://bucket/results/job_123/run_4.zip
        """
        if s3_url.startswith("s3://"):
            # s3://bucket/key format
            parts = s3_url[5:].split("/", 1)
            if len(parts) == 2:
                return parts[1]
        elif "s3.amazonaws.com/" in s3_url:
            # https://bucket.s3.amazonaws.com/key format
            return s3_url.split("s3.amazonaws.com/")[1]

        raise ValueError(f"Invalid S3 URL format: {s3_url}")

    def _sanitize_credentials(self, error_message: str) -> str:
        """
        Remove AWS credentials from error messages.

        Redacts:
        - AWS Access Keys (AKIA...)
        - AWS Secrets (base64 strings 40+ chars)
        - Signatures and tokens

        Returns:
            Error message with credentials replaced by [REDACTED_KEY] and [REDACTED]
        """
        # Pattern 1: AWS Access Key IDs (AKIA followed by 16 alphanumeric chars)
        message = re.sub(
            r"AKIA[A-Z0-9]{16}",
            "[REDACTED_KEY]",
            error_message
        )

        # Pattern 2: AWS Secrets and signatures (40+ char base64-like strings)
        message = re.sub(
            r"[A-Za-z0-9+/=]{40,}",
            "[REDACTED]",
            message
        )

        # Pattern 3: XML/JSON credential fields
        message = re.sub(
            r"<AWSAccessKeyId>[^<]+</AWSAccessKeyId>",
            "<AWSAccessKeyId>[REDACTED_KEY]</AWSAccessKeyId>",
            message
        )

        message = re.sub(
            r'"AWSAccessKeyId":\s*"[^"]+"',
            '"AWSAccessKeyId": "[REDACTED_KEY]"',
            message
        )

        return message
```

**Testing Strategy:**
```python
# Unit tests with mocked S3 client
def test_upload_results_success():
    """Test successful upload returns correct S3 URL."""
    mock_s3 = Mock()
    repo = S3ResultsRepository(mock_s3, "test-bucket")

    result = repo.upload_results(job_id=123, run_id=4, zip_content=b"fake zip")

    mock_s3.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="results/job_123/run_4.zip",
        Body=b"fake zip",
        ContentType="application/zip",
    )
    assert result.url == "https://test-bucket.s3.amazonaws.com/results/job_123/run_4.zip"

def test_upload_sanitizes_credentials_in_error():
    """Test credential sanitization when S3 upload fails."""
    mock_s3 = Mock()
    mock_s3.put_object.side_effect = ClientError(
        {"Error": {"Message": "Invalid AWSAccessKeyId: AKIAIOSFODNN7EXAMPLE"}},
        "PutObject"
    )

    repo = S3ResultsRepository(mock_s3, "test-bucket")

    with pytest.raises(ResultsStorageError) as exc_info:
        repo.upload_results(123, 4, b"zip")

    # Verify credentials were redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in str(exc_info.value)
    assert "[REDACTED_KEY]" in str(exc_info.value)
```

---

### 5. Domain Exception Hierarchy

**Design:**
```python
class ResultsUploadError(Exception):
    """Base exception for results upload operations."""
    pass


class InvalidResultsDirectoryError(ResultsUploadError):
    """Raised when results directory is invalid or empty."""
    pass


class ResultsPackagingError(ResultsUploadError):
    """Raised when ZIP creation fails."""
    pass


class ResultsStorageError(ResultsUploadError):
    """Raised when S3 upload fails."""

    def __init__(self, message: str, sanitized: bool = True):
        super().__init__(message)
        self.sanitized = sanitized  # Flag indicating if credentials were removed


class ResultsMetadataError(ResultsUploadError):
    """Raised when database update fails after successful upload."""

    def __init__(self, message: str, orphaned_s3_url: str):
        super().__init__(message)
        self.orphaned_s3_url = orphaned_s3_url  # For cleanup/recovery
```

**Exception Flow:**
```
upload_results() use case
    │
    ├─► FredResultsPackager.package_directory()
    │   ├─► InvalidResultsDirectoryError (directory not found)
    │   └─► ResultsPackagingError (ZIP creation fails)
    │
    ├─► S3ResultsRepository.upload_results()
    │   └─► ResultsStorageError (S3 upload fails, credentials sanitized)
    │
    └─► RunRepository.save()
        └─► ResultsMetadataError (DB update fails, S3 orphaned)
```

---

### 6. ITimeProvider Interface

**Design:**
```python
from datetime import datetime
from typing import Protocol


class ITimeProvider(Protocol):
    """Protocol for time/clock operations."""

    def now_utc(self) -> datetime:
        """Get current UTC datetime."""
        ...


class SystemTimeProvider:
    """Production time provider using system clock."""

    def now_utc(self) -> datetime:
        return datetime.utcnow()


class FixedTimeProvider:
    """Test time provider with fixed datetime."""

    def __init__(self, fixed_time: datetime):
        self._time = fixed_time

    def now_utc(self) -> datetime:
        return self._time
```

**Usage in Tests:**
```python
def test_upload_sets_correct_timestamp():
    """Verify upload_results sets results_uploaded_at correctly."""
    # Arrange
    fixed_time = datetime(2025, 10, 23, 19, 56, 0)
    time_provider = FixedTimeProvider(fixed_time)

    # Act
    upload_results(
        ...
        time_provider=time_provider
    )

    # Assert
    assert run.results_uploaded_at == fixed_time  # Exact match!
```

---

### 7. Refactored upload_results() Use Case

**Clean Architecture Version:**
```python
from datetime import datetime
from pathlib import Path

from epistemix_platform.models.run import RunStatus
from epistemix_platform.repositories.interfaces import (
    IResultsRepository,
    IRunRepository,
)
from epistemix_platform.services.interfaces import (
    IResultsPackager,
    ITimeProvider,
)
from epistemix_platform.exceptions import (
    InvalidResultsDirectoryError,
    ResultsMetadataError,
    ResultsStorageError,
)


def upload_results(
    run_repository: IRunRepository,
    results_packager: IResultsPackager,
    results_repository: IResultsRepository,
    time_provider: ITimeProvider,
    job_id: int,
    run_id: int,
    results_dir: Path,
) -> str:
    """
    Upload FRED simulation results to S3.

    This is a USE CASE (orchestration) function - it delegates all implementation
    details to services and repositories.

    Steps:
    1. Validate run exists and belongs to job
    2. Package results directory into ZIP
    3. Upload ZIP to S3
    4. Update run metadata
    5. Handle failures with proper error types

    Args:
        run_repository: Repository for run persistence
        results_packager: Service for packaging results into ZIP
        results_repository: Repository for S3 results storage
        time_provider: Service for getting current time
        job_id: Job identifier
        run_id: Run identifier
        results_dir: Path to results directory

    Returns:
        S3 URL where results were uploaded

    Raises:
        ValueError: If run not found or doesn't belong to job
        InvalidResultsDirectoryError: If results directory is invalid
        ResultsStorageError: If S3 upload fails
        ResultsMetadataError: If database update fails after upload
    """
    # Step 1: Validate run exists
    run = run_repository.find_by_id(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    if run.job_id != job_id:
        raise ValueError(f"Run {run_id} does not belong to job {job_id}")

    # Step 2: Package results (delegates to service)
    packaged = results_packager.package_directory(results_dir)
    # Raises: InvalidResultsDirectoryError, ResultsPackagingError

    # Step 3: Upload to S3 (delegates to repository)
    upload_location = results_repository.upload_results(
        job_id=job_id,
        run_id=run_id,
        zip_content=packaged.zip_content,
    )
    # Raises: ResultsStorageError (with sanitized credentials)

    # Step 4: Update run metadata
    run.results_url = upload_location.url
    run.results_uploaded_at = time_provider.now_utc()
    run.status = RunStatus.DONE

    try:
        run_repository.save(run)
    except Exception as e:
        # Database failed AFTER successful upload = orphaned S3 file
        raise ResultsMetadataError(
            f"Results uploaded to S3 but database update failed: {e}",
            orphaned_s3_url=upload_location.url
        ) from e

    return run.results_url
```

**Key Improvements:**
- ✅ Only 50 lines (vs. 160 in Phase 1)
- ✅ Cyclomatic complexity = 3 (vs. 8)
- ✅ Pure orchestration, no implementation details
- ✅ Clear dependency injection
- ✅ Proper error types
- ✅ Testable time handling

---

## Testing Strategy for Phase 4

### Test Layers

1. **Unit Tests (Isolation)**
   ```
   ├── test_fred_results_packager.py
   │   ├── Test with single RUN directory
   │   ├── Test with multiple RUN directories
   │   ├── Test with empty directory (should fail)
   │   └── Test with nonexistent directory (should fail)
   │
   ├── test_s3_results_repository.py
   │   ├── Test upload success (mock S3 client)
   │   ├── Test upload failure (ClientError)
   │   ├── Test credential sanitization
   │   ├── Test download URL generation
   │   └── Test S3 URL parsing
   │
   └── test_upload_results_use_case.py (already exists)
       ├── Test successful upload workflow
       ├── Test run not found
       ├── Test invalid results directory
       ├── Test S3 upload failure
       ├── Test database update failure (orphaned file)
       └── Test IAM credentials vs. presigned URLs
   ```

2. **Integration Tests**
   ```
   test_upload_results_integration.py
   ├── Test with real file system (tmp_path fixture)
   ├── Test with S3 mock (moto library)
   ├── Test with real PostgreSQL database
   └── Test complete workflow end-to-end
   ```

3. **Contract Tests**
   ```
   test_results_repository_protocol.py
   ├── Verify S3ResultsRepository implements IResultsRepository
   ├── Verify all methods match protocol signature
   ```

---

## Implementation Checklist for Phase 4

### Step 1: Create Domain Exceptions ✅
- [ ] Create `epistemix_platform/src/epistemix_platform/exceptions.py`
- [ ] Define `ResultsUploadError` base exception
- [ ] Define `InvalidResultsDirectoryError`
- [ ] Define `ResultsPackagingError`
- [ ] Define `ResultsStorageError`
- [ ] Define `ResultsMetadataError`
- [ ] Add unit tests for exception hierarchy

### Step 2: Create Time Provider ✅
- [ ] Create `epistemix_platform/src/epistemix_platform/services/time_provider.py`
- [ ] Define `ITimeProvider` protocol
- [ ] Implement `SystemTimeProvider`
- [ ] Implement `FixedTimeProvider` (for tests)
- [ ] Add to services `__init__.py` exports

### Step 3: Create Results Packager ✅
- [ ] Create `epistemix_platform/src/epistemix_platform/services/results_packager.py`
- [ ] Define `PackagedResults` dataclass
- [ ] Define `IResultsPackager` protocol
- [ ] Implement `FredResultsPackager`
- [ ] Add unit tests (single dir, multiple dirs, edge cases)
- [ ] Add to services `__init__.py` exports

### Step 4: Implement S3 Results Repository ✅ (CRITICAL)
- [ ] Create `epistemix_platform/src/epistemix_platform/repositories/s3_results_repository.py`
- [ ] Implement `S3ResultsRepository` class
- [ ] Implement `upload_results()` method
- [ ] Implement `_sanitize_credentials()` method
- [ ] Implement `get_download_url()` method
- [ ] Implement `_generate_results_key()` helper
- [ ] Implement `_extract_key_from_url()` helper
- [ ] Add comprehensive unit tests (especially credential sanitization!)
- [ ] Add to repositories `__init__.py` exports

### Step 5: Refactor upload_results Use Case ✅
- [ ] Stash current implementation
- [ ] Rewrite `upload_results()` following design above
- [ ] Add `results_packager` parameter
- [ ] Add `time_provider` parameter
- [ ] Remove deprecated `upload_location_repository` parameter
- [ ] Update docstring
- [ ] Verify all 6 existing tests still pass

### Step 6: Update CLI Integration ✅
- [ ] Update `epistemix_platform/src/epistemix_platform/cli.py`
- [ ] Create `FredResultsPackager` instance
- [ ] Create `SystemTimeProvider` instance
- [ ] Create `S3ResultsRepository` instance
- [ ] Update `upload_results` call with new dependencies
- [ ] Handle new exception types in CLI error display

### Step 7: Add New Edge Case Tests ✅
- [ ] Test orphaned file tracking (ResultsMetadataError)
- [ ] Test credential sanitization in logs
- [ ] Test with very large ZIP files
- [ ] Test concurrent uploads (idempotency)
- [ ] Test S3 bucket permissions errors

### Step 8: Integration Testing ✅
- [ ] Test with real temp directories
- [ ] Test with moto (S3 mock)
- [ ] Test with real PostgreSQL database
- [ ] Test complete workflow

### Step 9: Staging Validation ✅
- [ ] Deploy to staging
- [ ] Run manual test with real simulation
- [ ] Verify S3 file created correctly
- [ ] Verify database updated correctly
- [ ] Check logs for credential leakage
- [ ] Test download URL generation

---

## Success Criteria

**Phase 4 is complete when:**

1. ✅ All 6 existing tests pass
2. ✅ New unit tests pass (packager, repository, exceptions)
3. ✅ Integration tests pass
4. ✅ No credential leakage in logs (verified with grep)
5. ✅ Cyclomatic complexity of upload_results < 4
6. ✅ Lines of code in upload_results < 50
7. ✅ Manual staging test succeeds
8. ✅ Code review by software-architect agent passes

---

## Risk Mitigation

**Risk 1: S3 permissions in staging**
- Mitigation: Test S3 operations in staging first
- Fallback: Use localstack for local S3 testing

**Risk 2: Credential sanitization regex insufficient**
- Mitigation: Comprehensive unit tests with real AWS error messages
- Fallback: Use allowlist approach (only log specific safe fields)

**Risk 3: Breaking existing callers**
- Mitigation: Keep deprecated parameter temporarily
- Fallback: Create wrapper function for backward compatibility

**Risk 4: Orphaned files accumulate**
- Mitigation: Log orphaned URLs for manual cleanup
- Future: Implement async cleanup job

---

## Next Phase: Clean Rebuild

Phase 4 will implement this design from scratch, keeping only the tests from Phase 1.

**Approach:**
1. Stash Phase 1 prototype code
2. Keep only test files
3. Implement components in order (exceptions → services → repository → use case)
4. Run tests incrementally (TDD)
5. Integration test
6. Staging validation

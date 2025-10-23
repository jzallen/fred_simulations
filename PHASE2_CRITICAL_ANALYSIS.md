# Phase 2: Critical Analysis - Upload Results Architecture

## Overview
This document provides a critical analysis of the Phase 1 prototype implementation, identifying core responsibilities, tangled concerns, missing abstractions, and architectural improvements needed for Phase 4 clean rebuild.

**Date:** 2025-10-23
**Branch:** `zallen/fred-31-add-epistemix-cli-command-to-upload-simulation-results-to-s3`
**Phase:** Phase 2 - Critical Analysis
**Status:** Analysis in progress

---

## Core Responsibilities Analysis

### What the System SHOULD Do

The upload results feature has **3 core responsibilities**:

1. **Results Validation & Packaging**
   - Validate simulation run exists and belongs to correct job
   - Validate results directory contains valid FRED output
   - Package results into ZIP format for storage

2. **Results Storage**
   - Upload ZIP to S3 using server-side credentials (IAM role)
   - Generate stable S3 URL for results retrieval
   - Handle upload failures gracefully

3. **Metadata Persistence**
   - Update run record with results URL
   - Record upload timestamp
   - Update run status to DONE
   - Handle database failures (orphaned files)

### Current Implementation - Tangled Concerns

The current `upload_results()` use case mixes ALL THREE responsibilities:

```
upload_results() [160+ lines]
├── Responsibility 1: Validation & Packaging [~80 lines]
│   ├── Run validation (lines 50-56)
│   ├── Directory validation (lines 58-79)
│   └── ZIP creation (lines 82-103)
├── Responsibility 2: Storage [~15 lines]
│   └── S3 upload (lines 110-119)
└── Responsibility 3: Persistence [~30 lines]
    └── Database update (lines 121-130)
    └── Error handling (lines 126-160)
```

**Problem:** The use case is doing **implementation** work instead of **orchestration** work.

---

## Tangled Concerns

### 1. File System Operations in Use Case

**Location:** Lines 58-96

**Tangled Concern:**
```python
# This is FILE SYSTEM logic, not BUSINESS logic
run_dirs = [p for p in results_dir.glob("RUN*") if p.is_dir()]
single_run_dir = results_dir.name.upper().startswith("RUN") and results_dir.is_dir()

if not run_dirs and not single_run_dir:
    raise ValueError(
        f"No FRED output directories (RUN*) found in {results_dir}. "
        "Pass the parent directory containing RUN*/ subdirectories or a single RUN* directory."
    )
```

**Why It's Wrong:**
- Use case knows about Path objects, glob patterns, directory structures
- FRED-specific conventions ("RUN*") leaked into domain layer
- Cannot swap file system for testing without complex mocking

**Should Be:**
```python
# Use case orchestrates, doesn't implement
results_package = results_packager.package_directory(results_dir)
# results_packager handles all file system details
```

---

### 2. ZIP Creation Logic in Use Case

**Location:** Lines 82-96

**Tangled Concern:**
```python
# This is DATA SERIALIZATION logic, not ORCHESTRATION logic
with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
    for file_path in results_dir.rglob("*"):
        if file_path.is_file():
            if run_dirs:
                arcname = file_path.relative_to(results_dir)
            else:
                arcname = Path(results_dir.name) / file_path.relative_to(results_dir)
            zip_file.write(file_path, arcname=arcname.as_posix())
```

**Why It's Wrong:**
- Complex conditional logic for arcname calculation
- Direct zipfile manipulation
- Algorithm embedded in use case instead of service

**Should Be:**
```python
# Use case gets a ZIP package from a service
zip_content = results_packager.create_zip(validated_results)
```

---

### 3. S3 Upload Without Credential Sanitization

**Location:** Lines 110-119

**Critical Security Issue:**
```python
try:
    upload_location = results_repository.upload_results(
        job_id=job_id,
        run_id=run_id,
        zip_content=zip_buffer.getvalue(),
    )
except Exception as e:
    raise ValueError(f"Failed to upload results to S3: {e}") from e
```

**Why It's Wrong:**
- Exception `e` might contain AWS credentials in error message
- No sanitization before logging
- Could leak IAM credentials in logs/monitoring

**From FRED-34 Discovery:**
Error messages contained: `AWSAccessKeyId>AKIASPPQVVXSB2AKJUFE`

**Should Be:**
```python
# Repository sanitizes errors before raising
# OR use case explicitly sanitizes before logging
except ResultsUploadError as e:
    # e.message already sanitized by repository
    logger.error(f"Upload failed: {e.sanitized_message}")
    raise
```

---

### 4. Database Transaction Without S3 Rollback

**Location:** Lines 110-130

**Distributed Transaction Problem:**
```python
# Step 1: Upload to S3 (succeeds)
upload_location = results_repository.upload_results(...)

# Step 2: Update database (might fail)
run_repository.save(run)  # <-- If this fails, S3 file is orphaned
```

**Why It's Wrong:**
- No atomicity guarantee
- No compensation mechanism
- No idempotency (retry would create duplicate S3 files)

**Should Be:**
```python
# Use saga pattern or two-phase commit simulation
try:
    # Phase 1: Upload (get URL but don't commit in DB)
    s3_url = results_repository.upload_results(...)

    # Phase 2: Commit in database
    run.results_url = s3_url
    run_repository.save(run)

except DatabaseError:
    # Compensation: Mark S3 file for cleanup
    results_repository.mark_for_deletion(s3_url)
    raise
```

---

## Missing Abstractions

### 1. Missing: ResultsPackager Service

**Needed Abstraction:**
```python
@dataclass
class PackagedResults:
    """Value object representing packaged simulation results."""
    zip_content: bytes
    file_count: int
    total_size_bytes: int
    checksum: str  # MD5 or SHA256

class IResultsPackager(Protocol):
    """Service for packaging FRED simulation results."""

    def package_directory(self, results_dir: Path) -> PackagedResults:
        """
        Package a results directory into a ZIP file.

        Validates:
        - Directory exists and contains FRED output
        - At least one RUN* directory or is itself a RUN* directory
        - Files are readable

        Returns:
        - PackagedResults value object with ZIP content and metadata

        Raises:
        - InvalidResultsDirectoryError if validation fails
        """
        ...
```

**Why Needed:**
- Encapsulates file system operations
- Provides testable boundary
- Returns value object instead of raw bytes
- Single Responsibility Principle

---

### 2. Missing: S3ResultsRepository Implementation

**Currently:** Only interface exists, NO implementation!

**Needed Implementation:**
```python
class S3ResultsRepository:
    """Repository for server-side S3 results uploads."""

    def __init__(self, s3_client: boto3.client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def upload_results(
        self,
        job_id: int,
        run_id: int,
        zip_content: bytes
    ) -> UploadLocation:
        """
        Upload results ZIP to S3 using IAM credentials.

        S3 Key Format: results/job_{job_id}/run_{run_id}.zip

        Error Handling:
        - Sanitizes AWS credentials from error messages
        - Re-raises as ResultsUploadError with clean message
        """
        object_key = f"results/job_{job_id}/run_{run_id}.zip"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=zip_content,
                ContentType="application/zip",
            )
        except ClientError as e:
            # CRITICAL: Sanitize credentials before logging
            sanitized_msg = self._sanitize_credentials(str(e))
            raise ResultsUploadError(sanitized_msg) from e

        url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"
        return UploadLocation(url=url)

    def _sanitize_credentials(self, error_msg: str) -> str:
        """Remove AWS credentials from error messages."""
        # Remove access keys: AKIA...
        msg = re.sub(r"AKIA[A-Z0-9]{16}", "[REDACTED_KEY]", error_msg)
        # Remove secrets/signatures (40+ chars base64)
        msg = re.sub(r"[A-Za-z0-9+/=]{40,}", "[REDACTED]", msg)
        return msg
```

**Why Critical:**
- Production code would fail without this
- Security vulnerability (credential leakage)
- Can't test real S3 operations

---

### 3. Missing: Domain Exception Hierarchy

**Currently:** Everything throws `ValueError`

**Needed Exceptions:**
```python
class ResultsUploadError(Exception):
    """Base exception for results upload failures."""
    pass

class InvalidResultsDirectoryError(ResultsUploadError):
    """Raised when results directory is invalid."""
    pass

class ResultsStorageError(ResultsUploadError):
    """Raised when S3 storage fails."""
    pass

class ResultsMetadataError(ResultsUploadError):
    """Raised when database update fails after upload."""

    def __init__(self, message: str, orphaned_s3_url: str):
        super().__init__(message)
        self.orphaned_s3_url = orphaned_s3_url
```

**Why Needed:**
- Callers can distinguish error types
- Enables proper retry logic
- Allows compensation actions (cleanup orphaned files)

---

### 4. Missing: TimeProvider / Clock Abstraction

**Currently:** Direct `datetime.utcnow()` call

**Needed Abstraction:**
```python
class ITimeProvider(Protocol):
    """Abstraction for time/clock operations."""

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

**Why Needed:**
- Tests can verify exact timestamps
- Enables time-travel testing
- Makes temporal dependencies explicit

---

## Well-Structured Components (Keep These)

### 1. Test Structure ✅

**File:** `test_upload_results.py`

**What's Good:**
- Clear Gherkin-style scenario descriptions
- Proper arrange-act-assert structure
- Comprehensive edge case coverage (6 scenarios)
- Good use of fixtures for test data

**Example:**
```python
def test_successfully_upload_results_for_completed_simulation(...):
    """
    Given a completed simulation run exists with run_id 1
    And the results directory contains simulation output files
    When I upload results for job_id 123 and run_id 1
    Then the results should be zipped
    And the ZIP should be uploaded to S3
    """
```

**Why Keep:**
- Tests define behavior contract
- Can keep tests and rebuild implementation

---

### 2. Repository Interface (IResultsRepository) ✅

**File:** `epistemix_platform/src/epistemix_platform/repositories/interfaces.py`

**What's Good:**
- Clear separation: server-side uploads vs. client-side uploads
- Protocol-based interface (duck typing)
- Good documentation of IAM credentials vs. presigned URLs

**Keep Because:**
- Proper abstraction boundary
- Enables dependency inversion
- Runtime checkable with `@runtime_checkable`

---

### 3. Run Domain Model ✅

**File:** `epistemix_platform/src/epistemix_platform/models/run.py`

**What's Good:**
- Clean dataclass with proper fields
- `results_url` and `results_uploaded_at` fields exist
- Status enum with proper values

**Keep Because:**
- Domain model is stable
- Good separation of concerns
- Supports both persisted and unpersisted states

---

## Specific Design Flaws

### Flaw 1: Use Case as Implementation, Not Orchestrator

**Current:**
```python
def upload_results(...) -> str:
    # 160 lines of implementation details
    run = run_repository.find_by_id(run_id)
    if not results_dir.exists(): ...
    run_dirs = [p for p in results_dir.glob("RUN*") if p.is_dir()]
    with zipfile.ZipFile(...) as zip_file: ...
    upload_location = results_repository.upload_results(...)
    run_repository.save(run)
```

**Should Be:**
```python
def upload_results(...) -> str:
    # ~30 lines of orchestration
    run = run_repository.find_by_id(run_id)
    _validate_run_ownership(run, job_id)

    packaged = results_packager.package_directory(results_dir)
    upload_location = results_repository.upload_results(job_id, run_id, packaged.zip_content)

    run.results_url = upload_location.url
    run.results_uploaded_at = time_provider.now_utc()
    run.status = RunStatus.DONE
    run_repository.save(run)

    return run.results_url
```

**Improvement:**
- Use case down to ~30 lines
- Clear step-by-step orchestration
- Each step delegated to proper abstraction

---

### Flaw 2: No Credential Sanitization

**Current:**
```python
except Exception as e:
    raise ValueError(f"Failed to upload results to S3: {e}") from e
```

**Problem:** `str(e)` might be:
```
"SignatureDoesNotMatch: The request signature we calculated does not match
the signature you provided. Check your AWS Secret Access Key:
wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**Should Be:**
```python
except ClientError as e:
    sanitized = self._sanitize_credentials(str(e))
    logger.error(f"S3 upload failed: {sanitized}")
    raise ResultsStorageError(sanitized) from e
```

**Improvement:**
- Credentials removed before logging
- Specific exception type
- Security vulnerability fixed

---

### Flaw 3: Orphaned Files Not Tracked

**Current:**
```python
upload_location = results_repository.upload_results(...)  # S3 write
run_repository.save(run)  # DB write - might fail!
```

**Problem:** If database fails, S3 file exists but run.results_url is NULL.

**Should Be:**
```python
upload_location = results_repository.upload_results(...)

try:
    run_repository.save(run)
except DatabaseError as e:
    # Track orphaned file for cleanup
    orphaned_files_repository.record_orphan(
        s3_url=upload_location.url,
        job_id=job_id,
        run_id=run_id,
        created_at=time_provider.now_utc()
    )
    raise ResultsMetadataError(
        f"Upload succeeded but database update failed: {e}",
        orphaned_s3_url=upload_location.url
    ) from e
```

**Improvement:**
- Orphaned files tracked for cleanup
- Operator can identify and resolve
- Exception includes S3 URL for manual recovery

---

## Architecture Recommendations

### Recommended Layer Structure

```
┌─────────────────────────────────────────────────────────┐
│  Controller Layer (CLI)                                  │
│  - epistemix-cli jobs results upload                     │
│  - Handles user input, formatting, error display         │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  Use Case Layer (Application Logic)                      │
│  - upload_results()                                      │
│  - Orchestrates services, manages workflow               │
│  - ~30 lines, delegates to services                      │
└────┬──────────┬──────────┬──────────┬───────────────────┘
     │          │          │          │
┌────▼─────┐ ┌─▼────────┐ ┌▼────────┐ ┌▼──────────────────┐
│ Results  │ │ Results  │ │  Run    │ │  Time Provider    │
│ Packager │ │Repository│ │Repository│ │                   │
│ Service  │ │ (S3)     │ │  (DB)   │ │                   │
└──────────┘ └──────────┘ └─────────┘ └───────────────────┘
     │            │             │             │
┌────▼────────────▼─────────────▼─────────────▼─────────────┐
│  Infrastructure Layer                                      │
│  - File system (Path, zipfile)                            │
│  - AWS S3 (boto3)                                         │
│  - Database (SQLAlchemy)                                  │
│  - System clock (datetime)                                │
└───────────────────────────────────────────────────────────┘
```

**Key Principle:** Dependencies point **inward** (Dependency Inversion)
- Use case depends on IResultsPackager, IResultsRepository, IRunRepository
- Concrete implementations live in infrastructure layer
- Easy to swap implementations (testing, different storage backends)

---

## Complexity Metrics Comparison

### Current Implementation (Phase 1)

| Metric | Value | Target |
|--------|-------|--------|
| Lines of Code (use case) | 160 | <50 |
| Cyclomatic Complexity | 8 | <4 |
| Direct Dependencies | 7 | <5 |
| Responsibilities | 6 | 1 |
| Abstraction Level | Mixed | High |

### Target Architecture (Phase 4)

| Metric | Value |
|--------|-------|
| Lines of Code (use case) | ~30 |
| Cyclomatic Complexity | 3 |
| Direct Dependencies | 4 (packager, results_repo, run_repo, time) |
| Responsibilities | 1 (orchestration) |
| Abstraction Level | High (delegates to services) |

---

## Critical Path to Clean Architecture

**Priority 1 - Security (MUST FIX):**
1. Implement S3ResultsRepository with credential sanitization
2. Add comprehensive error sanitization tests
3. Audit all logging for credential leakage

**Priority 2 - Core Abstractions (SHOULD FIX):**
1. Extract ResultsPackager service
2. Implement domain exception hierarchy
3. Add TimeProvider abstraction

**Priority 3 - Distributed Transaction (NICE TO HAVE):**
1. Implement orphaned file tracking
2. Add cleanup job for orphaned S3 files
3. Add idempotency for retries

**Priority 4 - Code Quality (REFACTORING):**
1. Reduce use case to orchestration only
2. Remove deprecated `upload_location_repository` parameter
3. Add composite lookup `find_by_job_and_run_id()`

---

## Next Phase: Design Planning

Phase 3 will:
1. Sketch component interfaces (ResultsPackager, S3ResultsRepository)
2. Design class responsibilities and collaborations
3. Define exception hierarchy
4. Plan test strategy for Phase 4
5. Create implementation checklist

**No code in Phase 3** - just design artifacts and architecture diagrams.

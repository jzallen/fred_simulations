# Phase 1 Design Smells - Upload Results Implementation

## Overview
This document captures the design issues, code smells, and architectural problems discovered during Phase 1 (Red-Green-Refactor rapid prototype) of implementing server-side results upload functionality.

**Date:** 2025-10-23
**Branch:** `zallen/fred-31-add-epistemix-cli-command-to-upload-simulation-results-to-s3`
**Phase:** Phase 1 - Rapid Prototype (Complete)
**Status:** All 6 tests passing ✅

---

## Design Smells Discovered

### 1. **Mixed Responsibilities in Use Case**
**Location:** `epistemix_platform/src/epistemix_platform/use_cases/upload_results.py`

**Problem:**
The `upload_results()` use case is doing too much:
- Run validation (lines 50-56)
- Results directory validation with complex logic (lines 58-79)
- ZIP file creation with intricate path handling (lines 82-103)
- S3 upload orchestration (lines 110-119)
- Database update (lines 121-160)

**Smell:** God Function / Feature Envy
- The function has 160+ lines and handles 6 distinct responsibilities
- Complex ZIP creation logic with conditionals for single vs. multiple RUN directories
- Direct manipulation of file system paths and ZIP archives

**Impact:**
- Hard to test individual concerns in isolation
- Difficult to change one aspect without affecting others
- Violation of Single Responsibility Principle

---

### 2. **Leaky Abstraction - File System Details in Use Case**
**Location:** Lines 58-96 in `upload_results.py`

**Problem:**
The use case contains file system-specific logic:
```python
# Accept either parent dir containing RUN* subdirs or a single RUN* dir
run_dirs = [p for p in results_dir.glob("RUN*") if p.is_dir()]
single_run_dir = results_dir.name.upper().startswith("RUN") and results_dir.is_dir()
```

**Smell:** Primitive Obsession / Leaky Abstraction
- Use case knows about FRED-specific directory naming conventions ("RUN*")
- Direct glob() and Path manipulation in business logic
- Conditional logic based on directory structure

**Impact:**
- Use case is coupled to FRED's file organization
- Cannot easily change results packaging format
- Hard to mock file system operations in tests

**Better Approach:**
Extract to a `ResultsPackager` service or value object that encapsulates:
- Results validation
- ZIP creation
- Path normalization

---

### 3. **Backward Compatibility Hack**
**Location:** Line 30 in `upload_results.py`

**Problem:**
```python
def upload_results(
    run_repository: IRunRepository,
    results_repository: IResultsRepository,
    job_id: int,
    run_id: int,
    results_dir: Path,
    upload_location_repository: IUploadLocationRepository | None = None,  # Deprecated
) -> str:
```

**Smell:** Dead Parameter / Incomplete Refactoring
- Added `upload_location_repository` as deprecated optional parameter
- Not actually used in implementation (lines 110-119 use `results_repository`)
- Creates confusion about which repository to use

**Impact:**
- Misleading function signature
- Future developers might use the wrong repository
- Violates Interface Segregation Principle

**Why It Exists:**
To avoid breaking existing callers during rapid prototyping.

**Fix Needed:**
Remove the parameter entirely and update all callers.

---

### 4. **Missing Abstraction for Results Upload**
**Location:** Repository interfaces

**Problem:**
Before this change, there was NO separate abstraction for server-side results uploads. We reused `IUploadLocationRepository` which is designed for client-side presigned URL uploads.

**Smell:** Wrong Abstraction / Forced Fit
- Presigned URLs are for client uploads (job configs)
- Server uploads need direct boto3 with IAM credentials
- Different security models, different error handling

**Original Issue:**
The FRED-34 work discovered SignatureDoesNotMatch errors because we tried to use presigned URLs for server-side uploads.

**Fix Applied:**
Created `IResultsRepository` protocol with:
- `upload_results(job_id, run_id, zip_content)` - Direct boto3 upload
- `get_download_url(results_url, expiration)` - Presigned GET for downloads

**Impact:**
This was the fundamental architectural flaw that caused the original FRED-34 failure.

---

### 5. **Incomplete Implementation - No Concrete Repository**
**Location:** `epistemix_platform/src/epistemix_platform/repositories/`

**Problem:**
We added `IResultsRepository` interface but NO concrete implementation:
- No `S3ResultsRepository` class
- No boto3 upload logic
- No error sanitization for credential leakage

**Smell:** Interface Without Implementation / Incomplete Abstraction
- Tests pass using mocks
- Production code would fail at runtime
- Missing critical security features (credential sanitization)

**Status:**
**CRITICAL** - Must be implemented in Phase 4.

**Required Implementation:**
```python
class S3ResultsRepository:
    def upload_results(self, job_id, run_id, zip_content):
        # 1. Generate S3 key: results/job_{job_id}/run_{run_id}.zip
        # 2. Direct boto3 put_object() with IAM credentials
        # 3. Sanitize errors to remove AWS credentials
        # 4. Return UploadLocation with S3 URL
        pass
```

---

### 6. **Inconsistent Repository Method Names**
**Location:** Repository interfaces

**Problem:**
- `IRunRepository` uses `find_by_id(run_id)`
- Tests expected `get_by_job_and_run_id(job_id, run_id)`
- Confusion about which method to use

**Smell:** Inconsistent Interface / Naming Confusion
- Different repositories use different naming conventions
- "find" vs. "get" - semantic difference unclear
- Missing composite lookup by (job_id, run_id)

**Impact:**
- Had to fix tests to use `find_by_id` instead of `get_by_job_and_run_id`
- Current implementation doesn't validate job_id matches run.job_id properly

**Better Approach:**
Add `find_by_job_and_run_id()` method to `IRunRepository` for proper composite lookup.

---

### 7. **Error Handling Inconsistencies**
**Location:** Lines 102-103, 118-119, 126-160

**Problem:**
Different error wrapping strategies:
```python
# Pattern 1: Wrap with ValueError
except Exception as e:
    raise ValueError(f"Failed to create ZIP file: {e}") from e

# Pattern 2: Same pattern but different message
except Exception as e:
    raise ValueError(f"Failed to upload results to S3: {e}") from e

# Pattern 3: More complex with logging
except Exception as e:
    logger.exception("CRITICAL: Results uploaded to S3 but DB update failed")
    raise ValueError(f"Results uploaded to S3, but failed to update database: {e}") from e
```

**Smell:** Inconsistent Error Handling / Loss of Type Information
- All errors become `ValueError`
- Original exception type lost (though preserved with `from e`)
- Different levels of logging detail

**Impact:**
- Caller cannot distinguish between different failure types
- Network errors vs. validation errors vs. database errors all look the same
- Hard to implement proper retry logic

**Better Approach:**
Define domain-specific exceptions:
- `ResultsValidationError`
- `ResultsUploadError`
- `ResultsStorageError`

---

### 8. **Tight Coupling to datetime.utcnow()**
**Location:** Line 123

**Problem:**
```python
run.results_uploaded_at = datetime.utcnow()
```

**Smell:** Global State / Testability Issue
- Direct call to `datetime.utcnow()` makes timestamps hard to test
- Cannot easily verify exact timestamp in tests
- Time-dependent behavior is implicit

**Impact:**
- Tests cannot reliably check `results_uploaded_at`
- Cannot easily test timezone handling
- Makes debugging time-related issues harder

**Better Approach:**
Inject a clock/time provider or use dependency injection for time source.

---

### 9. **Magic String for S3 URL Construction**
**Location:** Line 122

**Problem:**
```python
run.results_url = upload_location.url
```

**Context:** The S3 URL format is constructed by the (not-yet-implemented) `S3ResultsRepository`:
- Expected format: `https://{bucket}.s3.amazonaws.com/results/job_{job_id}/run_{run_id}.zip`
- Key pattern: `results/job_{job_id}/run_{run_id}.zip`

**Smell:** Hidden Dependency / Magic String Pattern
- S3 key pattern is hardcoded somewhere (not visible in use case)
- No validation that URL matches expected pattern
- Fragile if S3 bucket structure changes

**Impact:**
- Use case doesn't know what URL format to expect
- No contract about URL structure
- Could break silently if repository implementation changes

---

### 10. **Missing Transaction Boundary**
**Location:** Lines 110-130

**Problem:**
The upload and database update are not atomic:
```python
# Step 1: Upload to S3 (line 112)
upload_location = results_repository.upload_results(...)

# Step 2: Update database (line 127)
run_repository.save(run)
```

**Smell:** Distributed Transaction / Orphaned Resources
- If database update fails, ZIP file is orphaned in S3
- No cleanup mechanism
- No idempotency guarantee

**Impact:**
- Test `test_upload_succeeds_but_database_update_fails` explicitly checks for this
- S3 storage costs for orphaned files
- Manual cleanup required

**Partial Mitigation:**
The code logs `CRITICAL: Results uploaded to S3 but DB update failed` (line 156), which helps operators identify orphaned files.

**Better Approach:**
- Implement saga pattern for compensation
- Add cleanup job for orphaned S3 files
- Or use database transaction + S3 upload in order that allows rollback

---

## Summary Statistics

**Total Design Smells:** 10
**Critical Issues:** 2 (Missing implementation, Security vulnerability)
**High Priority:** 4 (Mixed responsibilities, Leaky abstraction, Backward compatibility, Transaction boundary)
**Medium Priority:** 4 (Naming inconsistency, Error handling, Time coupling, Magic strings)

**Test Coverage:** ✅ 6/6 tests passing (100%)
**Existing Tests:** ✅ 23/23 test files passing

---

## Recommended Next Steps

**Phase 2: Critical Analysis**
1. Analyze core responsibilities and identify proper boundaries
2. Identify missing abstractions (ResultsPackager, TimeProvider, etc.)
3. Design proper exception hierarchy
4. Plan transaction/saga pattern for atomicity

**Phase 3: Design Planning**
1. Sketch clean architecture with proper separation
2. Define interfaces for ResultsPackager, S3ResultsRepository
3. Design error handling strategy
4. Plan migration path from deprecated parameters

**Phase 4: Clean Rebuild**
1. Implement S3ResultsRepository with credential sanitization
2. Implement ResultsPackager for ZIP creation
3. Refactor upload_results use case to orchestrate services
4. Remove deprecated `upload_location_repository` parameter
5. Add proper exception types
6. Implement cleanup for orphaned files
7. Add integration tests with real S3 (localstack)

---

## Code Quality Metrics

**Lines of Code:** 160+ (use case)
**Cyclomatic Complexity:** ~8 (too high for a use case)
**Dependencies:** 4 repositories + Path + datetime + zipfile + logging
**Testability:** Moderate (heavy mocking required)

**Target for Phase 4:**
- Use case: <50 lines
- Cyclomatic Complexity: <4
- Dependencies: 3 repositories + 2 services
- Testability: High (service abstractions)

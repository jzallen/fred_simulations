# Phase 2: Refactor S3UploadLocationRepository to use JobS3Prefix

## Overview
This is Phase 2 of the S3 artifact timestamp consistency initiative. Phase 1 (completed in PR #XX) updated `S3ResultsRepository` to use `JobS3Prefix` for consistent timestamps. This phase will extend the same pattern to `S3UploadLocationRepository` to ensure **ALL** job artifacts (configs, inputs, and results) use `job.created_at` as their S3 timestamp.

## Context
Currently, `S3UploadLocationRepository.get_upload_location()` generates S3 keys using `datetime.now(UTC)` at the time of each upload:

```python
# CURRENT BEHAVIOR (Phase 1 incomplete)
Job created at:        2025-10-23 21:15:00
├── job_config upload: 2025-10-23 21:15:01  ← Different timestamp!
├── run_4_config:      2025-10-23 21:16:05  ← Different timestamp!
└── run_4_results:     2025-10-23 21:15:00  ✅ Uses job.created_at (Phase 1)

# DESIRED BEHAVIOR (Phase 2 complete)
Job created at:        2025-10-23 21:15:00
├── job_config upload: 2025-10-23 21:15:00  ✅ Uses job.created_at
├── run_4_config:      2025-10-23 21:15:00  ✅ Uses job.created_at
└── run_4_results:     2025-10-23 21:15:00  ✅ Uses job.created_at
```

All artifacts for job 12 will be in `jobs/12/2025/10/23/211500/`, regardless of when they were actually uploaded.

## Goals
1. ✅ **Consistency**: All job artifacts share the same S3 prefix
2. ✅ **Discoverability**: Single S3 LIST operation finds all job artifacts
3. ✅ **Simplicity**: Bulk operations (archive, delete) become trivial
4. ✅ **Type Safety**: JobS3Prefix value object enforces correct usage

## Implementation Tasks

### 1. Update S3UploadLocationRepository
**File**: `epistemix_platform/src/epistemix_platform/repositories/s3_upload_location_repository.py`

**Changes**:
- [ ] Add `s3_prefix: JobS3Prefix` parameter to `get_upload_location()`
- [ ] Replace `datetime.now(UTC)` calls with `s3_prefix` methods:
  - `job_upload.context == "job_config"` → `s3_prefix.job_config_key()`
  - `job_upload.context == "job_input"` → `s3_prefix.job_input_key()`
  - `job_upload.context == "run_config"` → `s3_prefix.run_config_key(run_id)`
- [ ] Update docstrings to document new parameter

### 2. Update IUploadLocationRepository Protocol
**File**: `epistemix_platform/src/epistemix_platform/repositories/interfaces.py`

**Changes**:
- [ ] Update `get_upload_location()` signature: add `s3_prefix: JobS3Prefix` parameter
- [ ] Import `JobS3Prefix` from models

### 3. Update Use Cases
**Files**:
- `epistemix_platform/src/epistemix_platform/use_cases/submit_job_config.py`
- `epistemix_platform/src/epistemix_platform/use_cases/submit_run_config.py`

**Changes for BOTH use cases**:
- [ ] Add `job_repository: IJobRepository` dependency
- [ ] Fetch job: `job = job_repository.find_by_id(job_id)`
- [ ] Create prefix: `s3_prefix = JobS3Prefix.from_job(job)`
- [ ] Pass prefix to `upload_location_repository.get_upload_location(..., s3_prefix=s3_prefix)`
- [ ] Update docstrings

### 4. Update CLI Command
**File**: `epistemix_platform/src/epistemix_platform/cli/commands/jobs/uploads.py`

**Changes**:
- [ ] Update `download` command to pass `job_repository` to use cases
- [ ] Ensure dependency injection includes job repository

### 5. Update Controller
**File**: `epistemix_platform/src/epistemix_platform/controllers/job_controller.py`

**Changes**:
- [ ] Update `submit_job_config()` to inject `job_repository`
- [ ] Update `submit_run_config()` to inject `job_repository`

### 6. Test Updates (Estimated 20-25 tests)

#### S3UploadLocationRepository Tests
**File**: `epistemix_platform/tests/repositories/test_s3_upload_location_repository.py`

- [ ] Add `sample_prefix` fixture
- [ ] Update ALL existing tests to pass `s3_prefix` parameter
- [ ] Add new test class: `TestS3UploadLocationRepositoryWithJobS3Prefix`
  - [ ] Test job_config upload uses prefix
  - [ ] Test job_input upload uses prefix
  - [ ] Test run_config upload uses prefix
  - [ ] Test multiple uploads share same prefix

#### submit_job_config Tests
**File**: `epistemix_platform/tests/use_cases/test_submit_job_config.py`

- [ ] Add `mock_job_repository` fixture
- [ ] Add `sample_job` fixture
- [ ] Update ALL test signatures to include job_repository
- [ ] Update ALL test setups: `mock_job_repository.find_by_id.return_value = sample_job`
- [ ] Update ALL use case calls to include `job_repository=mock_job_repository`
- [ ] Add new test: "Verify job fetched and prefix created from job.created_at"

#### submit_run_config Tests
**File**: `epistemix_platform/tests/use_cases/test_submit_run_config.py`

- [ ] Add `mock_job_repository` fixture
- [ ] Add `sample_job` fixture
- [ ] Update ALL test signatures to include job_repository
- [ ] Update ALL test setups
- [ ] Update ALL use case calls
- [ ] Add new test: "Verify run_config uses job.created_at not run.created_at"

### 7. Integration Testing
- [ ] Deploy to staging environment
- [ ] Create test job and verify ALL artifacts land in same S3 directory
- [ ] Verify download command still works
- [ ] Verify presigned URLs are generated correctly

## Testing Strategy

### Behavioral Specifications (Gherkin)

**Scenario 1: Job config upload uses job.created_at**
```gherkin
Given a job with id=12 and created_at=2025-10-23 21:15:00
When I upload job_config.json
Then the S3 key is "jobs/12/2025/10/23/211500/job_config.json"
And NOT "jobs/12/2025/10/23/211501/job_config.json" (different second)
```

**Scenario 2: Run config upload uses job.created_at**
```gherkin
Given a job with created_at=2025-10-23 21:15:00
And a run with created_at=2025-10-23 21:16:30 (1.5 minutes later)
When I upload run_config.json
Then the S3 key is "jobs/12/2025/10/23/211500/run_4_config.json"
And uses job.created_at (21:15:00) NOT run.created_at (21:16:30)
```

**Scenario 3: All artifacts share same directory**
```gherkin
Given a job created at 2025-10-23 21:15:00
When I upload:
  - job_config.json at 21:15:01
  - job_input.zip at 21:15:03
  - run_4_config.json at 21:16:05
  - run_4_results.zip at 21:20:00
Then ALL artifacts are in: jobs/12/2025/10/23/211500/
```

## Risks and Mitigations

### Risk 1: Breaking Changes
**Impact**: Existing code depends on current `get_upload_location()` signature

**Mitigation**:
- Add `s3_prefix` as REQUIRED parameter (not optional)
- Compiler will catch all call sites that need updating
- Run full test suite before merging

### Risk 2: S3 Path Migration
**Impact**: Old artifacts in old paths, new artifacts in new paths

**Mitigation**:
- **Acceptable**: Old artifacts remain accessible at old paths
- New uploads use new consistent paths
- Optional: Migration script to move old artifacts (NOT required for Phase 2)

### Risk 3: Presigned URL Expiration
**Impact**: Presigned URLs for old paths might break if we move files

**Mitigation**:
- ✅ **No migration**: Keep old files in old locations
- Only NEW uploads use new paths
- Presigned URLs continue to work for old artifacts

## Success Criteria
- [ ] All tests pass (existing + new)
- [ ] No regressions in functionality
- [ ] All job artifacts land in same S3 directory
- [ ] Code follows clean architecture principles
- [ ] Documentation updated (docstrings, README if needed)

## Related
- **Phase 1 PR**: #XX (completed) - Updated S3ResultsRepository
- **Design Document**: `PHASE3_JOBS3PREFIX_ANALYSIS.md`
- **Original Issue**: Timestamp fragmentation in S3 artifact storage

## Estimated Effort
- **Implementation**: 4-6 hours
- **Testing**: 3-4 hours
- **Review & Integration**: 2-3 hours
- **Total**: ~10-13 hours

---

**Priority**: Medium (Phase 1 already provides partial solution)
**Labels**: `enhancement`, `clean-architecture`, `s3`, `technical-debt`
**Assignee**: TBD

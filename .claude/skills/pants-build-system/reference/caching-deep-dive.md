# Caching Deep Dive

## When to Read This

Read this reference when you need to understand:
- How Pants caching works at a deep level
- Why target addresses provide better caching than file paths
- Cache key generation and invalidation
- Local vs remote caching strategies
- Troubleshooting cache-related issues
- Optimizing cache hit rates for faster development

## The Critical Principle

**ALWAYS use target addresses, NEVER use file paths for test execution.**

This single principle has the biggest impact on cache effectiveness.

## How Caching Works

### Cache Fundamentals

Pants maintains a **process-level cache** where each test file execution is cached separately:

1. **Input Hashing**: Pants computes a hash of:
   - Test file content
   - All imported files (transitive dependencies)
   - Test configuration
   - Python interpreter version
   - pytest version and configuration

2. **Cache Lookup**: Before running a test, Pants checks if this exact hash exists in cache

3. **Cache Hit**: If found, returns cached result (pass/fail + output)

4. **Cache Miss**: If not found, runs test and caches result

5. **Invalidation**: When any input changes, hash changes, cache misses

### File-Level Granularity

Even when you run `pants test epistemix_platform:src-tests`, Pants caches **per test file**:

```
epistemix_platform:src-tests (target)
├── tests/test_models.py        [cached independently]
├── tests/test_repositories.py  [cached independently]
├── tests/test_api.py           [cached independently]
└── tests/test_utils.py         [cached independently]
```

**If you modify `test_models.py`, only that file re-runs. The others return cached results.**

## Target-Based vs File-Based Caching

### The Problem with File Paths

When you use file paths, Pants creates **different cache keys** than target addresses:

```bash
# Creates cache key: "target:epistemix_platform:src-tests -> file:test_models.py"
pants test epistemix_platform:src-tests

# Creates cache key: "file:epistemix_platform/tests/test_models.py"
pants test epistemix_platform/tests/test_models.py
```

These are **separate cache entries**. Running tests via file path doesn't benefit from target-based cache.

### Example Scenario

**Day 1:**
```bash
pants test epistemix_platform:src-tests
# Runs all 20 test files, caches each
```

**Day 2:**
```bash
# Edit one file
vim epistemix_platform/src/epistemix_platform/models/user.py

pants test epistemix_platform:src-tests
# Only re-runs 3 affected test files
# Returns cached results for 17 unaffected files
# Total time: ~5 seconds instead of ~30 seconds
```

**Day 3 (using file path - WRONG):**
```bash
pants test epistemix_platform/tests/test_models.py
# Creates NEW cache entry
# Doesn't use cached result from Day 1's target-based run
# Must execute test even if nothing changed
```

**Day 4 (back to target - RIGHT):**
```bash
pants test epistemix_platform:src-tests
# Uses cache from Day 1 and Day 2
# Returns cached results for all unchanged files
```

### Why This Happens

Pants uses the **invocation pattern** as part of the cache key to ensure correct behavior:

- **Target-based invocation**: "Run all tests in this target"
- **File-based invocation**: "Run this specific file"

These are semantically different operations, so they get different cache keys.

## Cache Keys in Detail

### What Contributes to a Cache Key

For a test file, the cache key includes:

**1. Source Code**
- Test file content
- All imported production code
- All imported test utilities
- Transitive imports (imports of imports)

**2. Dependencies**
- Python interpreter version
- pytest version
- All pytest plugins (pytest-mock, pytest-cov, etc.)
- Any fixtures from conftest.py

**3. Configuration**
- pytest.ini or pyproject.toml [tool.pytest.ini_options]
- Pants test configuration
- Environment variables that affect test behavior

**4. Invocation Context**
- Target address (if using target)
- File path (if using file)
- pytest arguments (passed after --)

**Example:**
```bash
# Different cache keys due to pytest arguments
pants test epistemix_platform:src-tests -- -v
pants test epistemix_platform:src-tests -- -vv
pants test epistemix_platform:src-tests -- -k test_user
```

### Cache Key Stability

Cache keys are **stable across runs** if inputs don't change:

```bash
# Run 1
pants test epistemix_platform:src-tests
# Cache miss, executes tests, stores results with key K1

# Run 2 (no changes)
pants test epistemix_platform:src-tests
# Key K1 matches, cache hit, returns stored results
```

But **unstable if invocation changes**:

```bash
# Run 1
pants test epistemix_platform:src-tests
# Cache key K1

# Run 2 (different target syntax)
pants test epistemix_platform/tests/test_models.py
# Cache key K2 (different from K1!)
```

## Local vs Remote Caching

### Local Cache

**Location:** `~/.cache/pants/`

**Characteristics:**
- Fast (local disk I/O)
- Private to your machine
- Persists across runs
- Cleaned with `pants clean-all`

**Default Configuration:**

Pants uses local cache by default, no configuration needed.

### Remote Cache

**Purpose:** Share cache across team members and CI/CD systems

**Benefits:**
- Team member A's test run benefits team member B
- CI builds can reuse local development cache
- Faster cold starts on new machines

**Configuration (example):**

```toml
[GLOBAL]
remote_cache_read = true
remote_cache_write = true
remote_store_address = "grpc://cache.example.com:1234"
```

**Not configured by default** - requires infrastructure setup.

### Cache Sharing Scenarios

**Scenario 1: Shared Team Cache**

Developer A:
```bash
pants test epistemix_platform:src-tests
# Runs tests, uploads results to remote cache
```

Developer B (5 minutes later):
```bash
pants test epistemix_platform:src-tests
# Downloads results from remote cache
# No local execution needed!
```

**Scenario 2: CI Reusing Local Cache**

Local development:
```bash
pants test epistemix_platform:src-tests
# Results uploaded to remote cache
```

CI pipeline:
```bash
pants test epistemix_platform:src-tests
# Downloads results from remote cache
# Only re-runs tests for files you changed
```

## Cache Warmth

### Cold Cache

A **cold cache** means no cached results exist:
- First run after `pants clean-all`
- First run on a new machine
- After major dependency updates

**Behavior:** All tests execute, results get cached

**Time:** Full execution time (e.g., 30 seconds)

### Warm Cache

A **warm cache** means cached results exist:
- Subsequent runs without code changes
- Runs after minor code changes (only affected tests re-run)

**Behavior:** Returns cached results, only re-runs affected tests

**Time:** Near-instant for unchanged tests (e.g., 2 seconds)

### Partially Warm Cache

**Most common scenario** in active development:
- Some tests have cached results
- Some tests are affected by recent changes

**Example:**
```bash
# 20 test files total
# You changed 2 production files
# 4 test files import those production files

pants test epistemix_platform:src-tests
# Returns cached results: 16 files (instant)
# Re-runs affected: 4 files (~6 seconds)
# Total time: ~6 seconds instead of ~30 seconds
```

### Warming the Cache

**Strategy:** Run all tests after major changes to populate cache

```bash
# After git pull, dependency update, or clean
pants test ::

# All tests run and cache
# Subsequent runs will be fast
```

**Best Practice:** Run `pants test ::` periodically (daily or after major merges) to maintain warm cache.

## Cache Optimization Strategies

### 1. Consistent Target Usage

**DO:**
```bash
# Always use the same target
pants test epistemix_platform:src-tests
pants test epistemix_platform:src-tests
pants test epistemix_platform:src-tests
```

**DON'T:**
```bash
# Mixing invocation styles fragments cache
pants test epistemix_platform:src-tests
pants test epistemix_platform/tests/test_models.py
pants test epistemix_platform::
```

### 2. Run from Top Down

Let Pants optimize with broad targets:

```bash
# Best: Run all tests, Pants uses cache for unchanged files
pants test ::

# Good: Run component tests
pants test epistemix_platform::

# Okay: Run specific target
pants test epistemix_platform:src-tests

# Avoid: Running individual files
pants test epistemix_platform/tests/test_models.py
```

### 3. Separate Fast and Slow Tests

Create separate targets for different test types:

```python
# Fast unit tests
python_tests(
    name="unit-tests",
    sources=["tests/unit/**/*.py"],
    timeout=60,
)

# Slow integration tests
python_tests(
    name="integration-tests",
    sources=["tests/integration/**/*.py"],
    timeout=300,
)
```

**Workflow:**
```bash
# During TDD: run fast tests frequently
pants test epistemix_platform:unit-tests

# Before commit: run all tests
pants test epistemix_platform::
```

**Cache Benefit:** Unit test cache doesn't invalidate when you change integration test files.

### 4. Use --changed-since in CI

Only test affected code:

```bash
# In CI pipeline
pants test --changed-since=origin/main

# Locally
pants test --changed-since=HEAD~1
```

**Cache Benefit:** Unchanged code uses cache even in CI.

### 5. Stable pytest Arguments

Keep pytest arguments consistent:

```bash
# Consistent - builds same cache
pants test epistemix_platform:src-tests -- -v

# Inconsistent - different cache keys
pants test epistemix_platform:src-tests -- -v
pants test epistemix_platform:src-tests -- -vv
pants test epistemix_platform:src-tests
```

## Incremental Development Workflow

### Typical Development Cycle

**1. Edit Code**
```bash
vim epistemix_platform/src/epistemix_platform/models/user.py
```

**2. Run Tests**
```bash
pants test epistemix_platform:src-tests
# Only tests depending on user.py re-run
# Other tests return cached results
```

**3. Edit More Code**
```bash
vim epistemix_platform/src/epistemix_platform/repositories/user_repo.py
```

**4. Run Tests Again**
```bash
pants test epistemix_platform:src-tests
# Only tests depending on user_repo.py re-run
# Tests for unchanged code still cached
```

### Cache Accumulation

As you work, cache accumulates:

**Day 1:** Run all tests (cold cache)
- 30 seconds
- 20 files cached

**Day 2:** Change 2 files
- 5 seconds (18 cached, 2 re-run)

**Day 3:** Change 1 different file
- 3 seconds (19 cached, 1 re-run)

**Day 4:** Change same file as Day 2
- 3 seconds (19 cached, 1 re-run)

**Day 5:** Run without changes
- 1 second (20 cached)

## Troubleshooting Cache Issues

### Problem: Cache Never Hits

**Symptoms:**
- Every test run takes full execution time
- No speed improvement on unchanged code

**Possible Causes:**

1. **Using file paths instead of targets**
   ```bash
   # Wrong
   pants test epistemix_platform/tests/*.py

   # Right
   pants test epistemix_platform:src-tests
   ```

2. **Changing pytest arguments**
   ```bash
   # Each creates different cache key
   pants test epistemix_platform:src-tests -- -v
   pants test epistemix_platform:src-tests -- -vv
   pants test epistemix_platform:src-tests
   ```

3. **Unstable environment**
   ```bash
   # If environment variables change, cache misses
   export SOME_VAR=value1
   pants test epistemix_platform:src-tests

   export SOME_VAR=value2
   pants test epistemix_platform:src-tests  # Different cache key
   ```

### Problem: Tests Re-run When They Shouldn't

**Symptoms:**
- Tests re-run even though nothing changed
- Cache seems to invalidate randomly

**Possible Causes:**

1. **Dependency changes**
   - Updated pytest or plugin version
   - Updated production dependency

2. **Configuration changes**
   - Modified pyproject.toml [tool.pytest.ini_options]
   - Modified pytest.ini
   - Modified conftest.py

3. **Timestamp-based code**
   ```python
   # This causes cache to invalidate every run
   import datetime
   NOW = datetime.datetime.now()  # Different every run!
   ```

4. **Non-hermetic tests**
   ```python
   # Tests that read/write files in source tree
   def test_something():
       with open("test_data.json", "w") as f:  # Modifies source!
           f.write(data)
   ```

### Problem: Cache Growing Too Large

**Symptoms:**
- `~/.cache/pants/` directory is very large (>10 GB)
- Disk space warnings

**Solution:**

```bash
# Clean all cache
pants clean-all

# Then warm cache again
pants test ::
```

**Prevention:**
- Pants automatically prunes old cache entries
- Configure cache size limits in `pants.toml` if needed

## Cache Inspection

### Check Cache Directory

```bash
# View cache size
du -sh ~/.cache/pants/

# List cache contents
ls -lh ~/.cache/pants/named_caches/
```

### Enable Cache Logging

```bash
# See cache hit/miss in output
pants --level=debug test epistemix_platform:src-tests 2>&1 | grep -i cache
```

### Force Cache Miss

```bash
# Ignore cache, re-run everything
pants test --force epistemix_platform:src-tests
```

## Best Practices Summary

1. **Always use target addresses** - Maximizes cache effectiveness
2. **Use consistent invocation patterns** - Same target, same args
3. **Run broad targets (`::`)** - Let Pants optimize
4. **Separate test types** - Unit vs integration targets
5. **Use `--changed-since` in CI** - Only test affected code
6. **Warm cache after major changes** - Run `pants test ::` periodically
7. **Avoid file-based invocations** - Except for one-off debugging
8. **Keep pytest args stable** - Don't vary `-v`, `-s`, etc.
9. **Write hermetic tests** - No side effects in source tree
10. **Trust Pants' caching** - It's smarter than manual optimization

## Advanced: Cache Internals

### Process Execution Cache

Pants caches at the **process level**:
- Each test file runs in separate process
- Process inputs → hash → cache key
- Process outputs (pass/fail, stdout, stderr) → cached value

### Cache Key Example

For `test_models.py`:
```
Cache Key = hash(
    test_models.py content,
    models/user.py content,
    models/organization.py content,
    conftest.py content,
    pytest version,
    pytest-mock version,
    Python interpreter version,
    target address,
    pytest arguments,
    ...
)
```

### Cache Storage

```
~/.cache/pants/
├── lmdb_store/              # Process execution results
├── named_caches/            # Named caches (pip, pex)
│   ├── pex/
│   └── pip/
└── setup/                   # Bootstrapped tools
```

### Cache Pruning

Pants automatically prunes cache based on:
- Least recently used (LRU)
- Maximum cache size
- Age of cache entries

Default: Keep cache entries accessed in last ~30 days.

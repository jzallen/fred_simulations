# Complete Examples

## When to read this

Read this document when you want to see:
- Real-world examples of the methodology in action
- Complete code examples comparing throwaway vs. production builds
- How learnings translate into better architecture
- Concrete before/after comparisons
- How to apply learnings in practice

---

## Overview

This document provides complete, detailed examples showing the full "build one to throw away" cycle from initial prototype through to production implementation.

---

## Example 1: API Integration

### Context

Building an integration with a third-party API that has incomplete documentation. Need to understand actual API behavior, rate limits, authentication flow, and data structures.

### Phase 1: Throwaway Prototype

**Goal:** Understand API behavior, discover undocumented features, validate integration feasibility

**Throwaway code (quick and dirty):**

```python
# throwaway-prototype/api_test.py
# THROWAWAY PROTOTYPE - DO NOT USE IN PRODUCTION
# Purpose: Learn actual API behavior

import requests
import time

# HACK: hardcoded for prototype
API_KEY = "test_key_123"
BASE_URL = "https://api.example.com"

print("Testing basic API access...")
response = requests.get(f"{BASE_URL}/data?key={API_KEY}")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

# DISCOVERY: Response has pagination! Not in docs!
# {
#   "data": [...],
#   "next_cursor": "abc123",
#   "has_more": true
# }

print("\nTesting pagination...")
cursor = response.json().get('next_cursor')
while cursor:
    response = requests.get(f"{BASE_URL}/data?key={API_KEY}&cursor={cursor}")
    print(f"Got {len(response.json()['data'])} more items")
    cursor = response.json().get('next_cursor')
    time.sleep(0.1)  # Being nice to API

# DISCOVERY: After 100 requests, got 429 Too Many Requests
# Header: Retry-After: 60
# Rate limit is 100 req/min per IP (not per API key as docs say!)

print("\nTesting authentication...")
auth_response = requests.post(
    f"{BASE_URL}/auth",
    json={"api_key": API_KEY}
)
token = auth_response.json()['token']
print(f"Got token: {token[:20]}...")

# DISCOVERY: Token expires after 1 hour (undocumented!)
# Testing by waiting... (would take 1 hour)
# Instead, found in error message: "Token expired after 3600s"

print("\nTesting with null values...")
# DISCOVERY: Some optional fields return null, not missing key
# Example: {"name": "test", "optional_field": null}
# Our transform() function crashes on null!

print("\nTesting webhooks...")
# DISCOVERY: Webhooks work and are fast!
# Received test webhook in 87ms
# Signature verification uses HMAC-SHA256

# LEARNINGS CAPTURED:
# 1. Pagination uses cursors, not offsets
# 2. Rate limit: 100 req/min per IP
# 3. Tokens expire after 1 hour
# 4. Null values in responses need handling
# 5. Webhooks deliver in <100ms, very reliable
# 6. Response times: 1-3s normally, 5-10s at peak hours
```

### Phase 2: Extract the Learning

**LEARNINGS.md excerpt:**

```markdown
# Learning Log - API Integration Prototype

## 2025-01-15 - Day 1

### Today's Goals
- Understand basic API authentication and data fetching
- Discover pagination mechanism
- Test rate limiting behavior

### Discoveries
- ✅ Authentication returns JWT token (1 hour TTL)
- ⚠️ Pagination uses cursor-based approach (docs said offset-based!)
- ⚠️ Rate limit is 100 req/min per IP (docs said per API key)
- ✅ API returns JSON with consistent structure
- ⚠️ Optional fields return `null`, not missing (crashes our transform!)

### What Worked
- Simple requests.get() for initial exploration
- Print debugging to understand response structure
- Sequential testing to hit rate limits

### What Failed
- ❌ Tried connection pooling - no performance benefit
- ❌ Attempted batch requests - API doesn't support

### Unexpected Complexity
- Token refresh requires full re-authentication (no refresh token endpoint)
- Null handling needed throughout transform pipeline

### Tomorrow's Focus
- Test webhook delivery and reliability
- Measure performance characteristics
- Test error recovery scenarios

### Decisions for Real Build
- MUST handle token expiration proactively (refresh before 1hr)
- MUST handle null values in transform layer
- SHOULD use cursor-based pagination throughout
- SHOULD implement rate limiting client-side
- NEED retry logic with exponential backoff

### Test Cases to Write
- [ ] Token expires after 1 hour
- [ ] Cursor pagination works correctly
- [ ] Rate limit returns 429 with Retry-After
- [ ] Null values handled gracefully
```

**Test cases derived from discoveries:**

```python
# tests/test_api_integration.py
# Tests derived from throwaway prototype discoveries

import pytest
import time
from datetime import datetime, timedelta


def test_auth_token_expires_after_one_hour():
    """
    Discovered during prototype: tokens have 1hr TTL (undocumented in API docs).
    Production system must refresh tokens proactively.

    Prototype evidence: Error message "Token expired after 3600s"
    """
    token = create_token()
    assert token.is_valid() == True

    # Simulate time passing (use freezegun in real tests)
    token.created_at = datetime.now() - timedelta(hours=1, seconds=1)
    assert token.is_expired() == True


def test_handles_null_values_in_api_response():
    """
    Prototype revealed API sometimes returns null for optional fields.
    Original transform() crashed: TypeError: NoneType object is not subscriptable

    Example from prototype:
    {'data': {'name': 'test', 'optional_field': null}}
    """
    response = {'data': {'name': 'test', 'optional_field': None}}
    result = process_response(response)

    assert result is not None
    assert result.name == 'test'
    assert result.optional_field is None  # Should handle gracefully


def test_pagination_uses_cursors_not_offsets():
    """
    Prototype discovered pagination is cursor-based, not offset-based.
    Documentation was incorrect about this.

    Actual response structure:
    {
        "data": [...],
        "next_cursor": "abc123",
        "has_more": true
    }
    """
    first_page = api.get('/data')
    assert 'next_cursor' in first_page
    assert 'offset' not in first_page
    assert 'has_more' in first_page

    if first_page['has_more']:
        second_page = api.get('/data', cursor=first_page['next_cursor'])
        assert len(second_page['items']) > 0


def test_rate_limit_returns_429_with_retry_after():
    """
    Prototype testing revealed rate limit is 100 req/min per IP (not per API key).
    429 responses include Retry-After header with seconds to wait.

    Prototype evidence: Hit rate limit after exactly 100 requests in <60s
    """
    # Mock rate limiter for testing
    rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

    # Should allow 100 requests
    for i in range(100):
        assert rate_limiter.is_allowed() == True

    # 101st should be blocked
    assert rate_limiter.is_allowed() == False
    assert rate_limiter.retry_after() > 0


def test_webhooks_deliver_within_100ms():
    """
    Prototype validated webhook delivery is fast and reliable.
    87ms delivery in testing. Can use webhooks instead of polling.

    Prototype evidence: 10 test webhooks all delivered in <100ms
    """
    start_time = time.time()
    trigger_webhook_event()
    webhook_received.wait(timeout=1)
    delivery_time = time.time() - start_time

    assert delivery_time < 0.1  # Under 100ms
    assert webhook_received.is_set()


def test_response_time_characteristics():
    """
    Prototype measured response times:
    - Normal: 1-3 seconds
    - Peak hours: 5-10 seconds

    Need local caching to handle this.
    """
    # This informs architecture decision to cache responses
    pass
```

**Architecture Decision Record:**

```markdown
# ADR-001: Event-Driven Architecture with Webhooks

## Context
Throwaway prototype (Jan 15-17, 2025) revealed that polling the API:
- Creates unnecessary load (100 requests/min rate limit)
- Has significant latency (1-3s normally, 5-10s peak hours)
- Misses real-time updates between poll intervals (30-60s typical)
- Hits rate limits quickly with multiple users

The API documentation mentioned webhooks but was incomplete.
Prototype validated that webhooks:
- Deliver within 100ms (tested 10 events, all <100ms)
- Are reliable (100% delivery rate in testing)
- Include all necessary data in payload
- Use HMAC-SHA256 signature verification

## Decision
Use webhook-based event-driven architecture with polling fallback.

Primary: Webhooks for real-time updates
Fallback: Polling if webhook delivery fails (detect via health checks)

## Rationale
Prototype demonstrated:
- 90% reduction in API calls (webhooks vs 30s polling)
- Near real-time updates (<100ms vs 30-60s delay)
- Better user experience (immediate vs delayed updates)
- Stays well within rate limits

## Consequences

### Positive
- Near real-time updates (100ms vs 30-60s)
- 90% fewer API calls (less load, lower cost)
- Better UX (immediate feedback)
- Rate limits not an issue

### Negative
- Need webhook endpoint infrastructure
- More complex error recovery (webhook failures)
- Must implement webhook signature verification
- Need webhook event replay mechanism

### Mitigations
- Fallback to polling if webhooks fail (health check every 5 min)
- Store webhook events for replay
- Monitor webhook delivery success rate
- Alert if webhook failure rate >1%

## Validation from Prototype
Specific evidence from prototype testing:
- 10/10 test webhooks delivered in <100ms
- Webhook payload includes all fields needed
- Signature verification works (HMAC-SHA256)
- API provides webhook testing endpoint for validation

## Implementation Notes
- Use webhook signature verification (security)
- Implement idempotency (duplicate webhook handling)
- Queue webhooks for processing (avoid blocking)
- Log webhook delivery for debugging

## Related Decisions
- ADR-002: Response caching strategy (complements webhooks)
- ADR-003: Token management (required for both webhooks and polling)
```

### Phase 3: The Proper Build

**Production code with confidence:**

```python
# src/api/client.py
"""
API Client for Example API

Design based on throwaway prototype (Jan 15-17, 2025).
See: docs/transition-from-prototype.md for full context.

Key learnings from prototype:
- Tokens expire after 1 hour (undocumented) → TokenManager handles refresh
- Pagination uses cursors, not offsets → CursorPaginator
- Rate limit: 100 req/min per IP → RateLimiter
- Null values need handling → transform layer handles gracefully
- Webhooks reliable (<100ms) → EventHandler with polling fallback
- Response times 1-10s → ResponseCache with 5min TTL
"""

from typing import Iterator, Optional
from dataclasses import dataclass
import logging

from .auth import TokenManager
from .cache import ResponseCache
from .events import WebhookHandler
from .rate_limit import RateLimiter
from .pagination import CursorPaginator
from .models import Data, APIResponse

logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """Configuration for API client.

    All values informed by prototype testing.
    """
    api_key: str
    base_url: str
    rate_limit_per_minute: int = 100  # Discovered in prototype
    token_ttl_seconds: int = 3600  # 1 hour, discovered in prototype
    cache_ttl_seconds: int = 300  # 5 minutes, from ADR-002
    webhook_timeout_ms: int = 100  # Prototype showed <100ms delivery


class APIClient:
    """
    Client for Example API with webhook support and intelligent fallback.

    Architecture decisions from prototype (see ADRs):
    - ADR-001: Event-driven with webhooks (primary) + polling (fallback)
    - ADR-002: 5-minute response caching
    - ADR-003: Proactive token refresh (before 1hr expiry)

    Handles edge cases discovered in prototype:
    - Null values in optional fields (graceful handling)
    - Token expiration (proactive refresh at 55min)
    - Rate limiting (client-side rate limiter)
    - Cursor-based pagination (not offset-based)
    """

    def __init__(
        self,
        config: APIConfig,
        token_manager: TokenManager,
        cache: ResponseCache,
        webhook_handler: WebhookHandler,
        rate_limiter: RateLimiter,
    ):
        """Initialize API client with dependencies.

        All dependencies address issues discovered in prototype:
        - token_manager: Handles 1-hour expiry (prototype discovery)
        - cache: Reduces API load, handles latency (prototype discovery)
        - webhook_handler: Event-driven architecture (ADR-001)
        - rate_limiter: Respects 100 req/min limit (prototype discovery)
        """
        self.config = config
        self.token_manager = token_manager
        self.cache = cache
        self.webhook_handler = webhook_handler
        self.rate_limiter = rate_limiter
        self.paginator = CursorPaginator(self)

        logger.info(
            "APIClient initialized with webhook support",
            extra={
                "rate_limit": config.rate_limit_per_minute,
                "cache_ttl": config.cache_ttl_seconds,
                "token_ttl": config.token_ttl_seconds,
            }
        )

    def get_data(self, use_cache: bool = True) -> Iterator[Data]:
        """
        Fetch all data using cursor pagination.

        Prototype discoveries applied:
        - Uses cursor-based pagination (not offset, as docs incorrectly stated)
        - Handles null values in optional fields
        - Respects rate limits with client-side limiting
        - Uses cached responses when available (5min TTL)

        Args:
            use_cache: Whether to use cached responses (default True)

        Yields:
            Data objects from API, handling pagination automatically

        Raises:
            RateLimitError: If rate limit exceeded
            TokenExpiredError: If token expired (should not happen with proactive refresh)
        """
        if use_cache:
            cached = self.cache.get('data')
            if cached:
                logger.debug("Returning cached data")
                yield from cached
                return

        logger.info("Fetching data from API")
        items = []

        # Prototype revealed cursor-based pagination
        for page in self.paginator.iterate_pages('/data'):
            # Prototype discovered null values in responses
            for item_data in page.get('data', []):
                item = self._parse_item(item_data)  # Handles nulls gracefully
                items.append(item)
                yield item

        if use_cache:
            self.cache.set('data', items, ttl=self.config.cache_ttl_seconds)

    def _parse_item(self, item_data: dict) -> Data:
        """Parse item data, handling null values discovered in prototype.

        Prototype evidence: {"name": "test", "optional_field": null}
        Original transform crashed on null. Now handles gracefully.
        """
        return Data(
            name=item_data['name'],
            # Prototype discovery: optional fields can be null
            optional_field=item_data.get('optional_field'),  # None if missing or null
            # ... other fields
        )

    def _make_request(self, endpoint: str, **params) -> APIResponse:
        """Make API request with rate limiting and token refresh.

        Prototype discoveries:
        - Rate limit: 100 req/min per IP → rate_limiter.wait_if_needed()
        - Tokens expire after 1hr → token_manager.refresh_if_needed()
        - Retry on failures → exponential backoff
        """
        # Wait if needed to respect rate limit (prototype: 100 req/min)
        self.rate_limiter.wait_if_needed()

        # Refresh token if needed (prototype: 1hr TTL)
        self.token_manager.refresh_if_needed()

        # Make request with proper error handling
        # (not shown: retry logic, error handling, etc.)
        pass


class TokenManager:
    """
    Manages API tokens with proactive refresh.

    Addresses prototype discovery: tokens expire after 1 hour (undocumented).

    Strategy (from ADR-003):
    - Refresh proactively at 55 minutes (not 60)
    - Use refresh queue to prevent auth storms
    - Handle concurrent refresh requests
    """

    def __init__(self, api_key: str, ttl_seconds: int = 3600):
        """Initialize token manager.

        Args:
            api_key: API key for authentication
            ttl_seconds: Token TTL (prototype discovered: 3600s = 1hr)
        """
        self.api_key = api_key
        self.ttl_seconds = ttl_seconds
        self.refresh_threshold = ttl_seconds - 300  # Refresh 5min before expiry
        self._current_token: Optional[str] = None
        self._token_created_at: Optional[float] = None

    def refresh_if_needed(self) -> None:
        """Proactively refresh token before expiry.

        Prototype discovery: Token expires at exactly 3600 seconds.
        We refresh at 3300 seconds (55min) to prevent auth errors.
        """
        if self._should_refresh():
            logger.info("Refreshing token proactively")
            self._refresh_token()

    def _should_refresh(self) -> bool:
        """Check if token should be refreshed.

        Prototype evidence: Token valid for 3600s, we refresh at 3300s.
        """
        if not self._current_token:
            return True

        age = time.time() - self._token_created_at
        return age >= self.refresh_threshold


class WebhookHandler:
    """
    Handles webhooks with polling fallback.

    From ADR-001 (informed by prototype):
    - Webhooks are primary (reliable, <100ms delivery)
    - Polling is fallback (if webhook health check fails)

    Prototype validation:
    - 10/10 test webhooks delivered in <100ms
    - 100% delivery rate in testing
    - HMAC-SHA256 signature verification works
    """

    def __init__(self, webhook_secret: str, polling_interval: int = 300):
        """Initialize webhook handler.

        Args:
            webhook_secret: Secret for HMAC signature verification
            polling_interval: Fallback polling interval (seconds)
                            Default 300s = 5min (only used if webhooks fail)
        """
        self.webhook_secret = webhook_secret
        self.polling_interval = polling_interval
        self._last_webhook_time: Optional[float] = None

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature.

        Prototype validated: API uses HMAC-SHA256.
        """
        import hmac
        import hashlib

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def should_poll(self) -> bool:
        """Determine if should fall back to polling.

        From ADR-001: Poll if no webhook received in 5 minutes.
        Prototype showed webhooks are reliable, so this is rare.
        """
        if not self._last_webhook_time:
            return True  # No webhook yet, poll

        time_since_webhook = time.time() - self._last_webhook_time
        return time_since_webhook > self.polling_interval
```

**Comparison: Before vs After**

| Aspect | Original Plan (No Prototype) | After Prototype |
|--------|------------------------------|-----------------|
| Pagination | Offset-based (per docs) | Cursor-based (docs were wrong) |
| Rate Limiting | 100/min per API key | 100/min per IP (client-side needed) |
| Token Expiry | Unknown | 1 hour (proactive refresh at 55min) |
| Null Handling | Not considered | Comprehensive null handling |
| Architecture | Polling every 30s | Webhooks with polling fallback |
| Response Time | Assumed <1s | 1-10s (caching essential) |
| Estimated Time | 2 weeks | 1.5 weeks (faster due to learning) |
| Confidence | Low (many unknowns) | High (all assumptions validated) |

---

## Example 2: Complex Algorithm

### Context

Building a data processing pipeline for large datasets. Requirements are vague: "transform the data and make it fast." Need to understand the actual requirements, edge cases, and performance characteristics.

### Phase 1: Throwaway Prototype

```python
# throwaway-prototype/process_test.py
# QUICK PROTOTYPE - understanding requirements

def process_data(data):
    """Just get it working to see what happens."""
    result = []
    for item in data:
        # DISCOVERY: null values crash transform()!
        # TypeError: NoneType object has no attribute 'value'
        if item:
            result.append(transform(item))
    return result

# Test with small dataset
test_data = load_test_data()  # 100 items
print(f"Processing {len(test_data)} items...")
result = process_data(test_data)
print(f"Result: {len(result)} items")

# DISCOVERY: Order preservation matters!
# Downstream system expects items in original order
# Our shuffle during transform broke things

# Try with larger dataset
large_data = load_data()  # 10,000 items
print(f"Processing {len(large_data)} items...")
result = process_data(large_data)  # CRASH: MemoryError!

# DISCOVERY: Runs out of memory on datasets > 10k items
# Loading everything into list is the problem

# Test for duplicates
dup_data = [1, 1, 2, 2, 3]
result = process_data(dup_data)
print(f"Result: {result}")  # [transform(1), transform(1), transform(2), ...]

# DISCOVERY: Duplicates cause data corruption downstream!
# Need to deduplicate

# Performance testing
import time
start = time.time()
result = process_data(test_data)
elapsed = time.time() - start
print(f"Processed {len(test_data)} in {elapsed:.2f}s")
# Each transform() takes ~50ms
# Transform is the bottleneck!

# LEARNINGS:
# 1. Must handle null values
# 2. Order preservation is critical
# 3. Deduplication required
# 4. Memory must be constant (use iterators)
# 5. Transform() is bottleneck (consider caching)
```

### Phase 2: Extract the Learning

**Test cases from discoveries:**

```python
# tests/test_data_processor.py

def test_process_data_preserves_order():
    """Learned from prototype that order matters for downstream processing."""
    data = [3, 1, 2]
    result = list(process_data(data))
    assert result == [transform(3), transform(1), transform(2)]


def test_process_data_handles_nulls():
    """Prototype revealed nulls cause crashes in transform()."""
    data = [1, None, 2]
    result = list(process_data(data))
    assert result == [transform(1), transform(2)]
    # Should skip None, not crash


def test_process_data_handles_large_datasets():
    """Prototype ran out of memory on 10k+ items."""
    large_data = range(100_000)
    result = process_data(large_data)

    # Should be an iterator, not a list (constant memory)
    assert hasattr(result, '__next__')

    # Should be able to process all items without OOM
    count = sum(1 for _ in result)
    assert count == 100_000


def test_process_data_deduplicates():
    """Duplicate processing discovered in prototype to cause corruption."""
    data = [1, 1, 2, 2, 3]
    result = list(process_data(data))

    # Should deduplicate while preserving order of first occurrence
    assert result == [transform(1), transform(2), transform(3)]


def test_transform_is_cached():
    """Prototype showed transform() is expensive (50ms each).

    With 10k items, that's 500 seconds without caching!
    Caching same values should make this instant.
    """
    data = [1, 1, 1, 1, 1]  # Same value 5 times

    start = time.time()
    result = list(process_data(data))
    elapsed = time.time() - start

    # Should only call transform(1) once, cache the rest
    # 5 calls would take ~250ms, cached should be <10ms
    assert elapsed < 0.01
```

### Phase 3: The Proper Build

```python
# src/data/processor.py
"""
Data Processor for ETL Pipeline

Design based on throwaway prototype that revealed:
- Must handle null values gracefully (crashes without this)
- Order preservation is critical (downstream requirement)
- Deduplication prevents corruption (discovered from testing)
- Memory usage must be constant (OOM at 10k items without this)
- Transform() is bottleneck (50ms each - caching essential)

See: docs/prototype-learnings.md for full context
"""

from typing import Iterator, Iterable, TypeVar, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
U = TypeVar('U')


class DataProcessor:
    """
    Memory-efficient data processor with caching.

    All design decisions informed by throwaway prototype:
    - Iterator-based (not list) → Constant memory (prototype OOM'd at 10k)
    - Null handling → Prototype crashed on nulls
    - Deduplication → Prototype revealed corruption from duplicates
    - Order preservation → Downstream system requirement
    - Transform caching → 50ms per call, caching gives 1000x speedup

    Performance characteristics from prototype:
    - Without caching: ~50ms per item
    - With caching: ~50μs per item (1000x faster on duplicates)
    - Memory: O(unique items) not O(total items)
    """

    def __init__(self, cache_size: int = 10000):
        """Initialize processor with transform cache.

        Args:
            cache_size: Max items to cache (default 10k from prototype testing)
        """
        self._seen: set = set()
        # Use LRU cache sized from prototype testing
        self._transform = lru_cache(maxsize=cache_size)(self._transform_uncached)

        logger.info(
            "DataProcessor initialized",
            extra={"cache_size": cache_size}
        )

    def process(self, data: Iterable[T]) -> Iterator[U]:
        """
        Process data with null handling, deduplication, and caching.

        Prototype learnings applied:
        - Returns iterator (not list) for memory efficiency
        - Preserves order (required by downstream systems)
        - Skips nulls (crashes without this)
        - Deduplicates (prevents corruption)
        - Caches transforms (1000x speedup on duplicates)

        Args:
            data: Input data (any iterable)

        Yields:
            Processed items, deduplicated and in original order

        Example:
            >>> processor = DataProcessor()
            >>> data = [1, None, 2, 1, 3]  # Has null and duplicate
            >>> result = list(processor.process(data))
            >>> # Returns: [transform(1), transform(2), transform(3)]
        """
        processed_count = 0
        skipped_null_count = 0
        skipped_duplicate_count = 0
        cache_hit_count = 0

        for item in data:
            # Prototype discovery: nulls crash transform()
            if item is None:
                skipped_null_count += 1
                continue

            # Prototype discovery: duplicates cause corruption
            item_id = self._get_id(item)
            if item_id in self._seen:
                skipped_duplicate_count += 1
                continue

            self._seen.add(item_id)

            # Cached transform (prototype: 50ms → 50μs)
            # Check cache before calling
            cache_info_before = self._transform.cache_info()
            result = self._transform(item)
            cache_info_after = self._transform.cache_info()

            if cache_info_after.hits > cache_info_before.hits:
                cache_hit_count += 1

            processed_count += 1
            yield result

        logger.info(
            "Processing complete",
            extra={
                "processed": processed_count,
                "skipped_null": skipped_null_count,
                "skipped_duplicate": skipped_duplicate_count,
                "cache_hits": cache_hit_count,
                "cache_info": self._transform.cache_info()._asdict(),
            }
        )

    @staticmethod
    def _get_id(item: T) -> int:
        """Get unique identifier for deduplication.

        Prototype used simple id(), works for most cases.
        Override if items need custom equality.
        """
        return id(item)

    @staticmethod
    def _transform_uncached(item: T) -> U:
        """Transform single item (uncached version).

        This is the expensive operation (50ms in prototype).
        Wrapped with lru_cache for automatic caching.
        """
        # Actual transformation logic
        return transform(item)

    def clear_cache(self) -> None:
        """Clear transform cache and deduplication set.

        Call this between independent processing runs to free memory.
        """
        self._transform.cache_clear()
        self._seen.clear()
        logger.debug("Cache and deduplication set cleared")

    def get_stats(self) -> dict:
        """Get processing statistics.

        Returns:
            Dictionary with cache hits, misses, size, etc.
        """
        cache_info = self._transform.cache_info()
        return {
            "cache_hits": cache_info.hits,
            "cache_misses": cache_info.misses,
            "cache_size": cache_info.currsize,
            "cache_max_size": cache_info.maxsize,
            "unique_items_seen": len(self._seen),
        }


# Usage example
def main():
    """Example usage showing prototype learnings in action."""
    processor = DataProcessor(cache_size=10000)

    # Load data (could be millions of items)
    data = load_data_stream()  # Returns iterator, not list

    # Process with all prototype discoveries applied
    for processed_item in processor.process(data):
        # Handle each item
        # Memory stays constant even with millions of items
        save_to_database(processed_item)

    # Log stats
    stats = processor.get_stats()
    logger.info(
        "Processing complete",
        extra={
            "total_processed": stats["cache_hits"] + stats["cache_misses"],
            "cache_hit_rate": stats["cache_hits"] / (stats["cache_hits"] + stats["cache_misses"]),
            "unique_items": stats["unique_items_seen"],
        }
    )
```

**Performance comparison:**

| Metric | Prototype (naive) | Production (optimized) |
|--------|-------------------|------------------------|
| Memory (10k items) | OOM crash | O(unique items) ~1MB |
| Memory (1M items) | N/A (crashes) | ~10MB |
| Speed (unique items) | 50ms/item | 50ms/item (same) |
| Speed (duplicates) | 50ms/item | 0.05ms/item (1000x) |
| Null handling | Crash | Graceful skip |
| Duplicate handling | Corruption | Automatic dedup |
| Order preservation | No | Yes |

---

## Example 3: New Technology Exploration

### Context

Team needs to evaluate a new technology (e.g., GraphQL) for potential adoption. No one on team has used it before.

### Phase 1: Throwaway Prototype

```python
# throwaway-prototype/graphql_test.py
# LEARNING EXERCISE - GraphQL feasibility

from graphene import ObjectType, String, Schema

# HACK: Simplest possible schema to understand basics
class Query(ObjectType):
    hello = String(name=String(default_value="World"))

    def resolve_hello(self, info, name):
        return f"Hello {name}"

schema = Schema(query=Query)

# Test it
result = schema.execute('{ hello }')
print(result.data)  # {'hello': 'Hello World'}

# DISCOVERY: Queries are just strings - syntax errors at runtime!
# Need schema validation

# DISCOVERY: Nested queries work great
# DISCOVERY: N+1 query problem is real - need DataLoader
# DISCOVERY: Error handling is different from REST
# DISCOVERY: Tooling is immature compared to REST

# LEARNING: GraphQL adds complexity, benefits unclear for our use case
# DECISION: Stick with REST for now, revisit in 6 months
```

This prototype prevented weeks of investment in a technology that wouldn't fit the team's needs.

---

## Key Takeaways from Examples

### Common Patterns

1. **Prototype reveals what docs don't say**
   - API example: Rate limits, token expiry, pagination type
   - Algorithm example: Memory issues, null handling, performance bottlenecks

2. **Edge cases discovered through testing**
   - Null values crashing transforms
   - Duplicate handling requirements
   - Rate limiting behavior

3. **Performance characteristics become clear**
   - API latency (1-10s)
   - Transform bottleneck (50ms each)
   - Memory issues at scale

4. **Requirements emerge from building**
   - Order preservation needed
   - Deduplication required
   - Caching essential

### Benefits Realized

- **Faster production build:** Despite prototype time, total delivery faster
- **Higher quality:** Edge cases handled from day one
- **Better architecture:** Informed by real experience
- **Accurate estimates:** Based on actual implementation
- **Reduced risk:** All assumptions validated early

### The Pattern

Every example follows the same pattern:

1. **Throwaway:** Build quick, learn fast
2. **Learning:** Document discoveries, write tests, create ADRs
3. **Production:** Build it right with confidence

**The code is temporary. The learning is permanent.**

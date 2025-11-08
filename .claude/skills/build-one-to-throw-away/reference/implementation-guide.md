# Implementation Guide

## When to read this

Read this document when you're ready to actually implement "build one to throw away" and need:
- Step-by-step instructions for starting a throwaway prototype
- Templates for documentation and tracking
- Practical techniques for maintaining a learning log
- Transition procedures from prototype to production
- Specific commands and file structures

---

## Overview

This guide provides concrete, actionable steps for implementing the "build one to throw away" methodology. It includes templates, commands, and practical techniques you can use immediately.

---

## Before You Start

### When to Apply This Methodology

**USE this approach when:**
- Exploring completely new problem domains or technologies
- Requirements are vague or unclear
- Building with unfamiliar frameworks, languages, or tools
- Prototyping innovative features with uncertain feasibility
- First time implementing a particular type of system
- Need to validate assumptions quickly
- Stakeholders need proof-of-concept before commitment
- High technical uncertainty or risk
- The interesting software that isn't the fourth iteration of anything

**DO NOT use this approach when:**
- You've written three similar systems in a row
- Requirements are clear and well-understood
- Using familiar, proven technology stacks
- Under strict regulatory/compliance requirements
- Building incremental features on existing systems
- Time/budget doesn't allow for iteration

### Decision Checklist

Before starting a throwaway prototype, answer these questions:

- [ ] Are we exploring genuinely new territory?
- [ ] Is there significant technical uncertainty?
- [ ] Do we have unclear or vague requirements?
- [ ] Can we afford 20-40% of the production build time for learning?
- [ ] Is the same team available for both prototype and production?
- [ ] Can we resist pressure to productionize the prototype?

If you answered "yes" to most of these, proceed with the methodology.

---

## Step-by-Step Implementation

### Step 1: Set Up the Throwaway Project

Create a clearly separated throwaway directory:

```bash
# Create a separate throwaway directory - make it obvious
mkdir throwaway-prototype
cd throwaway-prototype

# Document the throwaway nature explicitly
cat > README.md << 'EOF'
# ⚠️ THROWAWAY PROTOTYPE - DO NOT USE IN PRODUCTION

## Historical Note
Following Fred Brooks' principle from "The Mythical Man-Month":
> "Plan to throw one away; you will, anyhow."

## Purpose
Validate [specific learning goal]

## Timeline
Started: [date]
Expected completion: [date - should be short!]
To be discarded on: [date]

## Learning Goals
- [ ] [Specific technical question to answer]
- [ ] [Specific requirement to discover]
- [ ] [Specific feasibility to validate]

## Learnings Captured
See: LEARNINGS.md (updated daily)
EOF
```

### Step 2: Create Learning Documentation Structure

Set up the documentation framework before writing any code:

```bash
# Create learning log
cat > LEARNINGS.md << 'EOF'
# Learning Log

## Learning Goals
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

---

## [Date] - Day 1

### Today's Goals
- [What you plan to learn today]

### Discoveries
- [Leave empty, fill as you learn]

### What Worked
- [Leave empty, fill as you learn]

### What Failed
- [Leave empty, fill as you learn]

### Tomorrow's Focus
- [Leave empty, fill at end of day]

### Decisions for Real Build
- [Leave empty, fill as you learn]

---
EOF

# Create decisions log
cat > DECISIONS.md << 'EOF'
# Architecture Decisions from Prototype

This document captures key architectural decisions informed by the prototype.
Will be converted to formal ADRs in the production build.

---
EOF

# Create test discoveries log
cat > TESTS.md << 'EOF'
# Test Cases Discovered

Edge cases and requirements discovered during prototyping.
Each will become a test in the production build.

## Edge Cases
- [ ] [Edge case description]

## Requirements Discovered
- [ ] [Requirement description]

## Performance Characteristics
- [ ] [Performance observation]

---
EOF
```

### Step 3: Write Throwaway Code

**Guidelines while coding:**

1. **Mark all hacks and shortcuts:**
```python
# HACK: hardcoded for prototype - real version needs config
API_KEY = "test_key_123"

# THROWAWAY: no error handling, assumes happy path
response = requests.get(url)
data = response.json()

# QUICK: should validate input in production
def process(item):
    return item.transform()  # assumes item is never None
```

2. **Use print statements liberally:**
```python
print(f"DEBUG: got {len(items)} items")
print(f"DEBUG: response structure: {response.keys()}")
print(f"DEBUG: took {elapsed}s")
```

3. **Keep it flat and simple:**
```python
# PROTOTYPE: flat code, no abstractions
# Real version will have proper architecture

def main():
    # Just get it working
    data = fetch_data()
    processed = process_data(data)
    results = analyze(processed)
    print(results)
```

### Step 4: Update Learning Log Daily

**At the end of each day (or after each major discovery):**

```bash
# Open LEARNINGS.md and add to today's entry
```

**Template for daily entries:**

```markdown
## [Date] - Day N

### Today's Goals
- Understand how pagination works
- Test rate limiting behavior
- Validate webhook reliability

### Discoveries
- ✅ Pagination uses cursor-based approach (not offset)
- ✅ Rate limit is 100 req/min per IP (not per API key as documented)
- ✅ Webhooks arrive within 100ms
- ⚠️ Auth tokens expire after 1 hour (undocumented!)
- ⚠️ Null values in response crash transform()

### What Worked
- Simple polling approach for initial testing
- Mock server for testing edge cases
- Using print statements to understand response structure

### What Failed
- ❌ Tried connection pooling - no performance benefit
- ❌ Attempted batch requests - API doesn't support
- ❌ Caching didn't help (data changes too frequently)

### Unexpected Complexity
- Token refresh requires full re-authentication flow
- Responses can take 5-10 seconds during peak hours
- Webhook signature verification is undocumented

### Tomorrow's Focus
- Test error recovery scenarios
- Validate webhook retry behavior
- Measure performance under load

### Decisions for Real Build
- MUST implement token refresh queue to avoid auth storms
- MUST handle null values in transform layer
- SHOULD use webhooks with polling fallback
- SHOULD cache responses for 5 minutes to reduce API load
- NEED comprehensive retry logic with exponential backoff

### Test Cases to Write
- [ ] Auth token expires after 1 hour
- [ ] Handle null values in optional fields
- [ ] Cursor-based pagination works correctly
- [ ] Rate limiting returns 429 with Retry-After
- [ ] Webhook signature verification
```

### Step 5: Capture Architecture Decisions

When you make a significant architectural decision based on learnings, document it:

```markdown
# DECISIONS.md

## Decision 1: Event-Driven Architecture

### Context
Prototype revealed that polling the API:
- Creates unnecessary load (100 requests/min limit)
- Has 5-10 second latency during peak hours
- Misses real-time updates between poll intervals

API provides webhooks but documentation incomplete.
Prototype validated webhooks are reliable (100ms delivery).

### Decision
Use webhook-based event-driven architecture with fallback polling.

### Rationale
- 90% reduction in API calls
- Near real-time updates (vs 30-60 second poll intervals)
- Better user experience
- Proven reliable in prototype

### Tradeoffs
- Need webhook endpoint infrastructure (added complexity)
- More complex error recovery
- Must implement webhook signature verification

### For Production Build
- Implement webhook handler with signature verification
- Add fallback polling for webhook failures
- Store webhook events for replay capability
- Monitor webhook health metrics

---

## Decision 2: Cache Response Data

### Context
Prototype showed:
- Same data requested frequently (80% cache hit rate)
- API responses take 1-3 seconds
- Rate limit makes frequent requests problematic

### Decision
Implement 5-minute response cache.

### Rationale
- Reduces API load by ~80%
- Improves response time from 1-3s to <10ms
- Stays within rate limits comfortably

### Tradeoffs
- Data can be up to 5 minutes stale
- Need cache invalidation strategy
- Memory usage for cache storage

### For Production Build
- Use Redis for distributed cache
- Implement cache invalidation on webhook events
- Add cache hit/miss metrics
- Configurable TTL per endpoint type
```

### Step 6: Convert Learnings to Test Cases

As you discover edge cases, write them as test cases:

```python
# test_api_integration.py
# Tests derived from throwaway prototype discoveries

def test_auth_token_expires_after_one_hour():
    """
    Discovered during prototype: tokens have 1hr TTL (undocumented in API docs).
    Production system must refresh tokens proactively.
    """
    token = create_token()
    time.sleep(3601)  # 1 hour + 1 second
    assert token.is_expired() == True


def test_handles_null_values_in_api_response():
    """
    Prototype revealed API sometimes returns null for optional fields.
    This was crashing the transform() function.
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
    """
    first_page = api.get('/data')
    assert 'next_cursor' in first_page
    assert 'offset' not in first_page

    second_page = api.get('/data', cursor=first_page['next_cursor'])
    assert len(second_page['items']) > 0


def test_rate_limit_returns_429_with_retry_after():
    """
    Prototype testing revealed rate limit is 100 req/min per IP.
    429 responses include Retry-After header.
    """
    # Make 101 requests rapidly
    for i in range(101):
        response = api.get('/data')
        if i < 100:
            assert response.status_code == 200

    # 101st should be rate limited
    assert response.status_code == 429
    assert 'Retry-After' in response.headers


def test_webhooks_deliver_within_100ms():
    """
    Prototype validated webhook delivery is fast and reliable.
    Can use webhooks instead of polling.
    """
    start_time = time.time()
    trigger_event()
    webhook_received.wait(timeout=1)  # Wait for webhook
    delivery_time = time.time() - start_time

    assert delivery_time < 0.1  # Under 100ms
```

---

## Transitioning to Production Build

### Step 7: Create Transition Document

Before discarding the prototype, create a comprehensive transition document:

```markdown
# Transition from Prototype to Production Build

## Prototype Summary
**Duration:** 3 days (Jan 15-17, 2025)
**Code written:** ~500 lines (to be discarded)
**Learning artifacts:**
- 15 test cases derived from discoveries
- 3 architecture decision records
- 1 API integration contract
- Performance benchmarks

## Timeline
- Started: 2025-01-15
- Completed: 2025-01-17
- Archived: 2025-01-17
- Production build start: 2025-01-18

## Key Learnings Applied

### 1. Token Management (ADR-001)
**Discovery:** Tokens expire after 1 hour (undocumented)
**Impact:** Need proactive refresh queue to avoid auth storms
**Test:** `test_auth_token_expires_after_one_hour()`

### 2. Event-Driven Architecture (ADR-002)
**Discovery:** Webhooks are reliable, polling is expensive
**Impact:** 90% reduction in API calls, near real-time updates
**Tests:** `test_webhooks_deliver_within_100ms()`, webhook suite

### 3. Null Handling (Multiple edge cases)
**Discovery:** API returns null for optional fields, crashes transform
**Impact:** Must handle nulls throughout transform pipeline
**Tests:** `test_handles_null_values_in_api_response()`

## Complexity Assessment

### Original Estimate (before prototype)
- Duration: 2 weeks
- Confidence: Low
- Risk: High (many unknowns)

### Revised Estimate (after prototype)
- Duration: 1.5 weeks
- Confidence: High
- Risk: Low (all assumptions validated)

**Time savings:** 0.5 weeks faster despite 3-day prototype
**Reason:** No discovery during implementation, no major refactoring

## Test Coverage from Prototype

### Edge Cases Discovered: 15
- [x] Auth token expiration
- [x] Null value handling
- [x] Rate limiting behavior
- [x] Pagination cursor handling
- [x] Webhook delivery timing
- [x] ... (10 more)

### Integration Scenarios Validated: 3
- [x] Full authentication flow
- [x] Webhook + polling fallback
- [x] Error recovery scenarios

### Performance Bottlenecks Identified: 2
- [x] Transform function (needs caching)
- [x] API latency during peak hours (need local cache)

## Risk Mitigation

### High-Risk Assumptions Validated
- ✅ API reliability under load (tested with 1000 req/hour)
- ✅ Webhook availability and reliability (99.9% delivery in tests)
- ✅ Token expiration handling (validated 1-hour TTL)
- ✅ Rate limiting behavior (confirmed 100 req/min)

### Risks Identified and Mitigated
- ⚠️ Peak hour latency → Mitigated with caching strategy
- ⚠️ Webhook failures → Mitigated with polling fallback
- ⚠️ Token refresh storms → Mitigated with refresh queue

## Architecture Decisions

See `DECISIONS.md` for full ADRs:
1. Event-driven architecture with webhooks
2. 5-minute response caching with Redis
3. Token refresh queue to prevent auth storms

## Production Build Plan

### Phase 1: Core Infrastructure (Days 1-2)
- Set up project structure with proper tooling
- Implement authentication with token refresh queue
- Set up Redis cache

### Phase 2: API Integration (Days 3-4)
- Webhook handler with signature verification
- Polling fallback mechanism
- Rate limiting and retry logic

### Phase 3: Data Processing (Days 5-6)
- Transform pipeline with null handling
- Caching layer for transform results
- Error recovery

### Phase 4: Testing & Polish (Days 7-8)
- All 15 test cases from prototype
- Integration tests
- Documentation

## Files to Preserve
- [x] `LEARNINGS.md` → Archived
- [x] `DECISIONS.md` → Convert to ADRs
- [x] `TESTS.md` → Implemented as test suite
- [x] Test cases → All 15 implemented
- [x] Performance benchmarks → Documented

## Prototype Archived
Location: `../archive/prototype-20250117/`
Status: Archived, not to be referenced for code

## Ready for Production Build
- [x] All learnings documented
- [x] Architecture decisions captured
- [x] Test cases written
- [x] Risks identified and mitigated
- [x] Estimates updated with confidence
- [x] Team aligned on approach
- [x] Prototype archived
```

### Step 8: Archive the Prototype

**Important:** Physically move the prototype away to prevent temptation:

```bash
# From project root
mkdir -p archive
mv throwaway-prototype archive/prototype-$(date +%Y%m%d)

# Verify it's archived
ls archive/

# Add note about archival
cat > archive/prototype-$(date +%Y%m%d)/ARCHIVED.md << 'EOF'
# ARCHIVED THROWAWAY PROTOTYPE

This prototype was archived on $(date).
DO NOT use any code from this prototype.

## Learnings Captured
See: ../production-build/docs/transition-from-prototype.md

## Why Archived (Not Deleted)
Kept for reference only - to understand what was tested,
but not to copy code from.
EOF
```

### Step 9: Start Production Build Fresh

Create a completely new, separate project:

```bash
# New production project - completely fresh start
mkdir production-build
cd production-build

# Set up proper project structure
mkdir -p {src,tests,docs,config}

# Copy only learning artifacts (not code)
cp ../archive/prototype-*/LEARNINGS.md docs/prototype-learnings.md
cp ../archive/prototype-*/DECISIONS.md docs/
cp ../archive/prototype-*/TESTS.md docs/

# Create transition document
# (use template from Step 7)

# Initialize with proper tooling
git init
# ... set up linting, formatting, testing, CI/CD, etc.
```

### Step 10: Implement with Confidence

Now build the production system using all your learnings:

```python
# src/api_client.py
# Built with confidence based on prototype learnings

from typing import Iterator
import time
from .auth import TokenManager  # Handles 1-hour expiry discovered in prototype
from .cache import ResponseCache  # 5-minute cache from ADR-002
from .webhooks import WebhookHandler  # Event-driven from ADR-002


class APIClient:
    """
    API client for Example API.

    Design based on throwaway prototype (Jan 15-17, 2025) that discovered:
    - Tokens expire after 1 hour (undocumented)
    - Pagination uses cursor-based approach
    - Rate limit is 100 requests/min per IP
    - Webhooks deliver within 100ms (reliable)
    - Null values in responses need explicit handling

    See: docs/transition-from-prototype.md for full context
    """

    def __init__(
        self,
        api_key: str,
        token_manager: TokenManager,
        cache: ResponseCache,
        webhook_handler: WebhookHandler
    ):
        self.api_key = api_key
        self.token_manager = token_manager  # Handles expiry discovered in prototype
        self.cache = cache  # From ADR-002
        self.webhook_handler = webhook_handler  # From ADR-002

    def get_data(self) -> Iterator[Data]:
        """
        Fetch all data using webhooks with polling fallback.

        Prototype validated webhooks are reliable (99.9% delivery).
        Falls back to polling if webhooks fail.
        """
        # Implementation using all prototype learnings
        pass
```

---

## Templates

### Template: Throwaway Project README

```markdown
# ⚠️ THROWAWAY PROTOTYPE - DO NOT USE IN PRODUCTION

## Historical Note
Following Fred Brooks' principle from "The Mythical Man-Month":
> "Plan to throw one away; you will, anyhow."

## Purpose
[One sentence describing what you're learning]

## Timeline
- Started: [YYYY-MM-DD]
- Expected completion: [YYYY-MM-DD] (should be 2-7 days)
- To be discarded: [YYYY-MM-DD]

## Learning Goals
- [ ] [Specific, measurable goal 1]
- [ ] [Specific, measurable goal 2]
- [ ] [Specific, measurable goal 3]

## Status
Current status: [In Progress / Learning Complete / Archived]

## Learnings Captured
- Daily log: `LEARNINGS.md` (updated daily)
- Decisions: `DECISIONS.md` (architectural choices)
- Tests: `TESTS.md` (edge cases discovered)

## Team
- [Name] - Builder (will also build production version)
- [Name] - Stakeholder

## Rules for This Prototype
- ✅ Speed over quality
- ✅ Hardcode values
- ✅ Skip error handling
- ✅ Print instead of log
- ✅ Focus on unknowns only
- ❌ No production polish
- ❌ No optimization
- ❌ No comprehensive tests
- ❌ No code reuse in production
```

### Template: Daily Learning Log Entry

```markdown
## [YYYY-MM-DD] - Day N

### Today's Goals
- [What you plan to validate/learn today]

### Discoveries
- ✅ [Confirmed assumption or new discovery]
- ⚠️ [Surprising finding that impacts design]
- ❌ [Failed assumption - impacts requirements]

### What Worked
- [Approach that succeeded]
- [Tool/technique that helped]

### What Failed
- ❌ [Approach that didn't work]
- ❌ [Why it failed]

### Unexpected Complexity
- [Something that's harder than expected]
- [Hidden requirement or edge case]

### Tomorrow's Focus
- [Next area to explore]
- [Question to answer]

### Decisions for Real Build
- MUST [Critical requirement discovered]
- SHOULD [Important but not critical]
- COULD [Nice to have discovered]
- NEED [Missing capability identified]

### Test Cases to Write
- [ ] [Edge case that needs test coverage]
- [ ] [Requirement that needs validation]
```

---

## Quick Reference

### Prototype Phase Checklist

**Before starting:**
- [ ] Confirmed this requires throwaway approach
- [ ] Set up separate throwaway directory
- [ ] Created README with learning goals
- [ ] Set up documentation structure (LEARNINGS.md, DECISIONS.md, TESTS.md)
- [ ] Communicated throwaway status to stakeholders

**During prototyping:**
- [ ] Updating LEARNINGS.md daily
- [ ] Marking all hacks and shortcuts in code
- [ ] Focusing only on learning goals
- [ ] Not over-engineering or polishing
- [ ] Capturing architecture decisions
- [ ] Writing test cases for edge cases

**After prototyping:**
- [ ] All learnings documented
- [ ] Test cases written for all edge cases
- [ ] Architecture decisions captured in ADRs
- [ ] Transition document created
- [ ] Prototype archived (not deleted, not in main codebase)
- [ ] Production build plan created

**Production build:**
- [ ] Starting fresh (not copying prototype code)
- [ ] Same team building production as built prototype
- [ ] All tests from prototype implemented
- [ ] All ADRs from prototype applied
- [ ] Learnings referenced in code comments

---

## Remember

**The code is temporary. The learning is permanent.**

This implementation guide provides structure, but adapt it to your needs. The key principles:
- Make throwaway status explicit
- Document learning continuously
- Focus on speed and learning, not quality
- Archive (don't delete or productionize) the prototype
- Build production fresh with confidence

# Phase Details: The Three-Phase Process

## When to read this

Read this document when you're ready to apply the "build one to throw away" methodology and need detailed guidance on:
- What to do in each phase
- What to skip vs. what to focus on
- How to extract maximum learning from your prototype
- How to transition from throwaway to production code

---

## Overview

The build-one-to-throw-away process consists of three distinct phases:

1. **Fast Prototype** - Learn as much as possible, as quickly as possible
2. **Extract the Learning** - Capture insights, not code
3. **The Proper Build** - Build it right using what you learned

---

## Phase 1: Fast Prototype (The Throwaway)

### Goal
Learn as much as possible, as quickly as possible

### Core Guidelines

1. **Speed over quality** - Cut every corner that doesn't teach you something
2. **Focus on unknowns** - Build only the parts where learning is needed
3. **Embrace quick-and-dirty** - Hardcode values, skip error handling, ignore edge cases
4. **No production concerns** - No logging, monitoring, documentation, or polish
5. **Different is good** - Consider using a language which can't be used in production to prevent stakeholders from trying to reuse the prototype code
6. **Stop at understanding** - The moment you understand the problem deeply, you're done

### What to Skip in the Throwaway

Deliberately avoid these production concerns:
- Comprehensive error handling
- Input validation beyond basics
- Performance optimization
- Security hardening
- Scalability considerations
- Proper logging and monitoring
- Clean code principles
- Extensive documentation
- Production deployment concerns
- Code reusability

### What to Focus On

Direct all energy toward learning:
- Core algorithm or business logic
- Technical feasibility validation
- API/integration verification
- User interaction patterns (if applicable)
- Identifying hidden complexity
- Discovering missing requirements
- Testing assumptions

### Why Speed is Essential

The most obvious reason for using throwaway prototyping is that it can be done quickly. If users can get quick feedback on their requirements, they may be able to refine them early in the development of the software. Making changes early in the development lifecycle is extremely cost effective since there is nothing at that point to redo.

### Practical Techniques

**When writing throwaway code:**
- Add comments like `# HACK: hardcoded for prototype`
- Use simple, straightforward approaches over clever ones
- Prefer flat code over abstractions
- Copy-paste is acceptable if it speeds learning
- Mock external dependencies liberally
- Use print statements instead of proper logging

### Timeline Expectations

A throwaway prototype should take **20-40% of the estimated final build time**. If you're spending more than that, you're likely over-engineering the prototype.

---

## Phase 2: Extract the Learning

### Goal
Capture insights, not code

### Why This Phase is Critical

This is the critical phase that distinguishes "build one to throw away" from wasted effort. The most value you get out of the first draft is the requirements you've gathered and preserved in the form of tests.

**Without this phase, the prototype is truly wasted effort.**

### Document What You Learned

Systematically capture insights across these dimensions:

1. **Requirements discovered** - What was unclear that is now clear?
2. **Technical insights** - What works? What doesn't?
3. **Architecture decisions** - What structure makes sense?
4. **Complexity hotspots** - Where is the real difficulty?
5. **Edge cases identified** - What did you miss initially?
6. **Performance characteristics** - Where are the bottlenecks?
7. **Integration points** - How do systems interact?
8. **Tests as specification** - Convert learnings into test cases

### Create Artifacts from the Throwaway

Transform learning into tangible artifacts:
- **Comprehensive test suite** - Requirements as tests
- **Architecture decision records (ADRs)** - Document key design choices
- **API contracts or interfaces** - Define clear boundaries
- **Data models and schemas** - Structure data properly
- **Sequence diagrams for complex flows** - Visualize interactions
- **Risk assessment document** - Identify and plan for risks
- **Refined requirements document** - Clarify what was vague

### Maintain a Learning Log

Keep a daily log during prototype development:

```markdown
# Learning Log

## [Date 1]

### Today's Discoveries
- Auth tokens expire after 1 hour (not documented in API)
- Rate limit is 100 req/min per IP, not per API key
- Pagination uses cursor-based, not offset-based approach
- Null values in response need explicit handling

### Unexpected Complexity
- Token refresh requires full re-authentication
- Responses can take 5-10 seconds during peak hours

### Failed Approaches
- Tried connection pooling - no performance benefit
- Attempted batch requests - API doesn't support

### Tomorrow's Focus
- Test error recovery scenarios
- Validate webhook reliability

### Decisions for Real Build
- Need robust retry logic with exponential backoff
- Must implement token refresh queue to avoid auth storms
- Should cache responses for 5 minutes to reduce API calls

## [Date 2]
...
```

### Convert Learnings to Tests

Every discovery should become a test case:

```python
# From prototype learning: "Auth tokens expire after 1 hour"
def test_auth_token_expires_after_one_hour():
    """Discovered during prototype: tokens have 1hr TTL (undocumented)."""
    token = create_token()
    time.sleep(3601)
    assert token.is_expired() == True

# From prototype learning: "Null values crash the transform"
def test_handles_null_values_in_api_response():
    """Prototype revealed API sometimes returns null for optional fields."""
    response = {'data': {'name': 'test', 'optional_field': None}}
    result = process_response(response)
    assert result is not None  # Should handle gracefully
```

### Document Architecture Decisions

Create ADRs based on prototype insights:

```markdown
# ADR 001: Use Event-Driven Architecture for API Integration

## Context
Throwaway prototype revealed that polling the API:
- Creates unnecessary load (100 requests/min limit)
- Has 5-10 second latency during peak hours
- Misses real-time updates between poll intervals

The API provides webhooks but documentation was incomplete.
Prototype validated that webhooks are reliable and provide
instant notifications.

## Decision
Use webhook-based event-driven architecture with fallback polling.

## Consequences
**Positive:**
- Near real-time updates (vs 30-60 second polling intervals)
- 90% reduction in API calls
- Better user experience

**Negative:**
- Need webhook endpoint infrastructure
- More complex error recovery (webhook failures)
- Must implement webhook signature verification

**Mitigations:**
- Fallback to polling if webhooks fail
- Store webhook events for replay
- Monitor webhook health metrics

## Validation from Prototype
Prototype demonstrated:
- Webhooks arrive within 100ms of events
- Webhook payload includes all necessary data
- API provides webhook testing endpoint
```

---

## Phase 3: The Proper Build

### Goal
Build it right using what you learned

### What You Can Do Now

Armed with prototype learnings, you can:
- Choose the right architecture with confidence
- Estimate accurately based on real experience
- Design proper abstractions and interfaces
- Anticipate edge cases and error conditions
- Build comprehensive test coverage from the start
- Make informed technology choices
- Set realistic expectations with stakeholders

### Build Quality In from the Start

The proper build should incorporate what you've learned while maintaining production quality from the start:

- Apply TDD with tests derived from prototype learnings
- Use proper design patterns and clean code practices
- Implement comprehensive error handling
- Consider security, performance, and scalability
- Write production-quality documentation
- Set up proper logging and monitoring

### Starting Fresh

**Important:** The proper build should be completely separate from the prototype:

```bash
# Archive the throwaway first
mkdir -p ../archive
mv ../throwaway-prototype ../archive/prototype-$(date +%Y%m%d)

# New, proper project - completely separate
mkdir proper-implementation
cd proper-implementation

# Start fresh with proper structure, tooling, and practices
# Apply all the learnings from the prototype
```

### Create a Transition Document

Document the transition from prototype to production:

```markdown
# Transition from Prototype to Production Build

## Prototype Summary
Duration: 3 days
Code written: ~500 lines (discarded)
Learning artifacts: 15 test cases, 3 ADRs, 1 API contract

## Key Learnings Applied
1. Token management requires refresh queue (see ADR-001)
2. Error handling must account for 5 failure modes (see tests)
3. Architecture uses event-driven approach (see ADR-002)

## Complexity Assessment
Original estimate: 2 weeks
Revised estimate: 1.5 weeks (faster due to prototype learnings)
Confidence: High (validated all major assumptions)

## Test Coverage from Prototype
- 15 edge cases discovered and now have test coverage
- 3 integration scenarios validated
- 2 performance bottlenecks identified and mitigated in design

## Risk Mitigation
All high-risk assumptions validated:
- ✅ API reliability under load
- ✅ Webhook availability and reliability
- ✅ Token expiration handling
- ✅ Rate limiting behavior
```

### Philosophy for the Proper Build

The various techniques and disciplines gathered around the banner of "agile" are on balance more honest at facing up to this unavoidable tension between planning and learning. The proper build should incorporate:

- **Validated architecture:** Based on real experience, not guesswork
- **Comprehensive tests:** Covering all edge cases discovered
- **Production quality:** Built right from the start
- **Clear design:** Informed by understanding the problem deeply
- **Realistic estimates:** Based on actual implementation experience

### Speed of the Proper Build

Counter-intuitively, the proper build should be **faster** than it would have been without the prototype because:
- You know exactly what needs to be built
- You've validated all major assumptions
- You've identified and mitigated technical risks
- You're not discovering requirements while building
- You've already made the key architectural decisions

---

## Success Criteria

You've successfully applied the three phases when:

✅ The throwaway was built in 20-40% of estimated final build time
✅ You discovered requirements or edge cases not in original spec
✅ You identified technical risks early
✅ The real build went faster than it would have without the prototype
✅ Tests in the real build reflect lessons from the throwaway
✅ You made better architectural choices than you would have initially
✅ The real build code is cleaner and better designed
✅ You resisted the temptation to reuse throwaway code
✅ The same team that built the throwaway built the real system
✅ You saved time and resources by finding issues early, preventing costly changes later

---

## Remember

**The hard part of software development is figuring out what to say, not how to say it** - the most value you get out of the first draft is the requirements you've gathered and preserved in the form of tests.

**You don't know what you don't know until you've built something.**

The throwaway version is a learning exercise, not a production artifact. Its purpose is to:
- Discover hidden requirements and edge cases
- Validate technical feasibility
- Understand the problem domain deeply
- Identify architectural pitfalls early
- Learn what "right" looks like
- Build technical capital by reducing early-stage technical debt accumulated from working with otherwise ill-fitting ideas

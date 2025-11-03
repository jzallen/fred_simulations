---
name: build-one-to-throw-away
description: Apply throwaway prototyping methodology when exploring new concepts, unfamiliar technology, or unclear requirements. Build fast, learn deeply, then rebuild properly. Use for feasibility studies, proof-of-concepts, and learning exercises.
version: 1.1.0
---

# Build One to Throw Away

## Historical Context

### The Origins: Fred Brooks and The Mythical Man-Month

This principle comes from Frederick Brooks' seminal 1975 book "The Mythical Man-Month: Essays on Software Engineering," based on his experiences managing IBM's OS/360 project in the 1960s. Brooks observed that complex software projects rarely get their fundamental design right on the first attempt, no matter how carefully planned.

**Brooks' original statement:**
> "Where a new system concept or new technology is used, one has to build a system to throw away, for even the best planning is not so omniscient as to get it right the first time. Hence plan to throw one away; you will, anyhow."

The OS/360 project was one of the largest software projects of its era, and Brooks witnessed firsthand how even the most experienced teams couldn't anticipate all the complexities and interactions in a large system until they had actually built something. This principle highlights the importance of early iteration and learning, even if it means discarding initial efforts.

### Brooks' Later Refinement

In the 1995 anniversary edition of The Mythical Man-Month, Brooks reflected on this principle and wrote: "This I now perceive to be wrong, not because it is too radical, but because it is too simplistic. The biggest mistake in the 'Build one to throw away' concept is that it implicitly assumes the classical sequential or waterfall model of software construction."

Brooks clarified that his original advice was meant for the waterfall development era, where teams would plan everything upfront and then build it all at once. In modern iterative development, we continuously refactor and rebuild - but we do it incrementally rather than throwing away an entire system.

**The key insight remains valid:** You learn by building, and your first attempt at solving a novel problem will reveal insights you couldn't have anticipated through planning alone.

### Modern Interpretation

Building a prototype or initial version that is expected to be thrown away can be seen as a form of risk management - it allows teams to identify and address major issues early when they are less costly and easier to fix.

Today, "build one to throw away" is best applied as:
- **Rapid throwaway prototypes** for exploring specific unknowns
- **Spike solutions** in Agile development for investigating technical questions
- **Proof-of-concept code** to validate feasibility before committing to a design
- **Learning exercises** when entering unfamiliar technical territory

The concept evolved alongside software engineering practices from waterfall to Agile, but the core truth endures: programmers aren't smart enough to get the core design choices right until they've built something that works.

## Philosophy

The hard part of software development is figuring out what to say, not how to say it - the most value you get out of the first draft is the requirements you've gathered and preserved in the form of tests.

**You don't know what you don't know until you've built something.**

The throwaway version is a learning exercise, not a production artifact. Its purpose is to:
- Discover hidden requirements and edge cases
- Validate technical feasibility
- Understand the problem domain deeply
- Identify architectural pitfalls early
- Learn what "right" looks like
- Build technical capital by reducing early-stage technical debt accumulated from working with otherwise ill-fitting ideas

### The Tension Brooks Identified

There's a terrible glaring conflict between what sensible managers want and what sensible programmers know. Managers want a plan - they want to lock in design constraints so that work can be dealt out and progress tracked and promises kept. Programmers know that they're not smart enough to get the core design choices right until they've built something that works.

The "build one to throw away" approach acknowledges this fundamental tension and provides a structured way to balance learning with delivery.

## When to Apply This Skill

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
- You've written three similar systems in a row - you'll probably go into the fourth with a pretty good grasp of what's important
- Requirements are clear and well-understood
- Using familiar, proven technology stacks
- Under strict regulatory/compliance requirements
- Building incremental features on existing systems
- Time/budget doesn't allow for iteration

**Brooks' Caveat:** If you've just written three driver-scheduling systems or foreign-exchange systems in a row, you'll probably go into the fourth with a pretty good grasp of what's important. Those kinds of systems matter. But the interesting software is by definition the stuff that isn't the fourth iteration of anything.

## The Build-One-To-Throw-Away Process

### Phase 1: Fast Prototype (The Throwaway)

**Goal:** Learn as much as possible, as quickly as possible

**Guidelines:**
1. **Speed over quality** - Cut every corner that doesn't teach you something
2. **Focus on unknowns** - Build only the parts where learning is needed
3. **Embrace quick-and-dirty** - Hardcode values, skip error handling, ignore edge cases
4. **No production concerns** - No logging, monitoring, documentation, or polish
5. **Different is good** - Consider using a language which can't be used in production to prevent stakeholders from trying to reuse the prototype code
6. **Stop at understanding** - The moment you understand the problem deeply, you're done

**What to skip in the throwaway:**
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

**What to focus on:**
- Core algorithm or business logic
- Technical feasibility validation
- API/integration verification
- User interaction patterns (if applicable)
- Identifying hidden complexity
- Discovering missing requirements
- Testing assumptions

**Speed is essential:** The most obvious reason for using throwaway prototyping is that it can be done quickly. If users can get quick feedback on their requirements, they may be able to refine them early in the development of the software. Making changes early in the development lifecycle is extremely cost effective since there is nothing at that point to redo.

### Phase 2: Extract the Learning

**Goal:** Capture insights, not code

This is the critical phase that distinguishes "build one to throw away" from wasted effort. The most value you get out of the first draft is the requirements you've gathered and preserved in the form of tests.

**Document what you learned:**
1. **Requirements discovered** - What was unclear that is now clear?
2. **Technical insights** - What works? What doesn't?
3. **Architecture decisions** - What structure makes sense?
4. **Complexity hotspots** - Where is the real difficulty?
5. **Edge cases identified** - What did you miss initially?
6. **Performance characteristics** - Where are the bottlenecks?
7. **Integration points** - How do systems interact?
8. **Tests as specification** - Convert learnings into test cases

**Create artifacts from the throwaway:**
- Comprehensive test suite (requirements as tests)
- Architecture decision records (ADRs)
- API contracts or interfaces
- Data models and schemas
- Sequence diagrams for complex flows
- Risk assessment document
- Refined requirements document

### Phase 3: The Proper Build

**Goal:** Build it right using what you learned

The various techniques and disciplines gathered around the banner of "agile" are on balance more honest at facing up to this unavoidable tension between planning and learning. The proper build should incorporate what you've learned while maintaining production quality from the start.

**Now you can:**
- Choose the right architecture with confidence
- Estimate accurately based on real experience
- Design proper abstractions and interfaces
- Anticipate edge cases and error conditions
- Build comprehensive test coverage from the start
- Make informed technology choices
- Set realistic expectations with stakeholders

**Build quality in from the start:**
- Apply TDD with tests derived from prototype learnings
- Use proper design patterns and clean code practices
- Implement comprehensive error handling
- Consider security, performance, and scalability
- Write production-quality documentation
- Set up proper logging and monitoring

## Anti-Patterns to Avoid

### ❌ "We'll just clean up the prototype"

Users can become confused between prototype and finished system, leading to expectations that the prototype can simply be polished into production code. Stakeholders without technical background may try to convince you to reuse the source code from the prototype, believing it will shorten the time required to release the product, but actually it will only delay the shipment date.

The technical debt and architectural compromises make this path more expensive than rebuilding.

### ❌ "Second-system effect"

Don't try to add every feature you thought of during the prototype. The second system effect occurs when you try to build a bigger, shinier, more complex system than the first one without the proper knowledge - there are many features that did not fit in the first project and were pushed into the second version, usually leading to overly complex and overly engineered systems.

Build the second version to the same scope with better implementation.

### ❌ "Plan to throw one away... and throw away two"

Brooks later warned that if you do indeed plan to throw one away, you'll end up throwing away two. This happens when:
- You assign the throwaway version to a mediocre programmer and switch programmers for "the real thing" - this discards the benefits of the learning exercise
- The learning from the throwaway doesn't transfer to the real implementation
- Management pressure causes premature productionization of prototype code

**Solution:** The same person/team who builds the throwaway should build the real system, bringing their hard-won insights with them.

### ❌ "Perfect prototype"

A key property of prototyping is that it's supposed to be done quickly. If developers lose sight of this fact, they very well may try to develop a prototype that is too complex. When the prototype is thrown away, the precisely developed requirements that it provides may not yield a sufficient increase in productivity to make up for the time spent developing the prototype.

Spending too much time making the prototype production-quality defeats the purpose.

### ❌ "Documentation-free throwaway"

If team members don't make a record of the work on time, others will not know about the change and the latest process of the project, thus the team may have to spend lots of time to re-communicate or re-do the work.

While the code is throwaway, the learnings must be captured.

## The Cultural Challenge

Embracing the "build one to throw away" philosophy requires a cultural shift in many organizations. It necessitates valuing learning and long-term project success over short-term efficiencies and outputs.

**For teams:**
- Foster a culture that views the initial development phase as a learning experience rather than just a product-building exercise to help align everyone's expectations and justify the need for early iterations
- Make throwaway status explicit in project naming and documentation
- Celebrate learning outcomes, not just working code
- Resist pressure to productionize prototypes

**For management:**
- Understand that initial "waste" prevents larger waste later
- Budget for learning iterations on novel projects
- Balance this approach with practical constraints like budgets and deadlines
- Trust that experienced teams will rebuild faster and better

## Implementation Guidelines for Claude Code

### Starting a Throwaway Prototype
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

### During Prototype Development

**When writing throwaway code:**
- Add comments like `# HACK: hardcoded for prototype`
- Use simple, straightforward approaches over clever ones
- Prefer flat code over abstractions
- Copy-paste is acceptable if it speeds learning
- Mock external dependencies liberally
- Use print statements instead of proper logging

**Maintain a learning log:**
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

### Transitioning to Real Build

**Before discarding the prototype:**

1. **Convert learnings to tests:**
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

2. **Document architecture decisions:**
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

3. **Create the real project structure:**
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

4. **Create a transition document:**
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

## Success Criteria

You've successfully applied "build one to throw away" when:

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

## Examples

### Example 1: API Integration

**Throwaway:**
```python
# Quick prototype - hardcoded everything to learn API behavior
import requests

# HACK: hardcoded for prototype
API_KEY = "test_key_123"
response = requests.get(f"https://api.example.com/data?key={API_KEY}")
print(response.json())  # Just print to see the structure

# Discovered: returns paginated results (not in docs!)
# Discovered: rate limits after 100 req (returns 429 with Retry-After)
# Discovered: authentication token expires after 1 hour
```

**Learning:** API returns paginated results, rate-limits after 100 requests, returns 429 with Retry-After header, tokens expire hourly

**Proper build:**
```python
# Based on prototype learnings
from typing import List, Iterator
import time

class APIClient:
    """API client with pagination and rate limiting.

    Designed based on throwaway prototype that discovered:
    - Pagination uses cursor-based approach
    - Rate limit is 100 requests/hour per API key
    - Tokens expire after 1 hour and require refresh
    """

    def __init__(self, api_key: str, rate_limiter: RateLimiter):
        self.api_key = api_key
        self.rate_limiter = rate_limiter
        self.token_expiry = None

    def get_all_data(self) -> Iterator[Data]:
        """Handles pagination and rate limiting discovered in prototype."""
        cursor = None
        while True:
            response = self._make_request('/data', cursor=cursor)
            yield from response.items
            if not response.has_more:
                break
            cursor = response.next_cursor

    def _make_request(self, endpoint: str, **params):
        """Handles rate limiting and token refresh."""
        self.rate_limiter.wait_if_needed()
        self._refresh_token_if_needed()
        # Proper error handling for 429, token expiry, etc.
```

### Example 2: Complex Algorithm

**Throwaway:**
```python
# Quick implementation to understand the problem
def process_data(data):
    # Just get it working to see what happens
    result = []
    for item in data:
        # Discovered: null values crash transform()
        # Discovered: order preservation matters for downstream
        # Discovered: duplicates cause data corruption
        # Discovered: runs out of memory on datasets > 10k items
        if item:
            result.append(transform(item))
    return result

# After running: "Ah! I now understand the real requirements"
```

**Learning:** Null handling is critical, order preservation required, deduplication needed, memory issues with large datasets, transform() is the bottleneck

**Proper build with tests:**
```python
# Tests derived from prototype discoveries
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

def test_process_data_handles_large_datasets():
    """Prototype ran out of memory on 10k+ items."""
    large_data = range(100_000)
    result = process_data(large_data)
    # Should be an iterator, not a list
    assert hasattr(result, '__next__')

def test_process_data_deduplicates():
    """Duplicate processing discovered in prototype to cause corruption."""
    data = [1, 1, 2]
    result = list(process_data(data))
    assert result == [transform(1), transform(2)]

# Now implement with proper architecture based on learnings
class DataProcessor:
    """Memory-efficient data processor.

    Design based on throwaway prototype that revealed:
    - Must handle null values gracefully
    - Order preservation is critical
    - Deduplication prevents corruption
    - Memory usage must be constant regardless of input size
    - Transform() is bottleneck and should be cached
    """

    def __init__(self):
        self._seen = set()
        self._transform_cache = {}

    def process(self, data: Iterable[Data]) -> Iterator[ProcessedData]:
        """Stream processing with deduplication and caching.

        Returns iterator for memory efficiency (prototype OOM'd on large inputs).
        Preserves order (required by downstream systems).
        Skips nulls (prototype crashed on nulls).
        Caches transforms (prototype showed this is the bottleneck).
        """
        for item in data:
            if item is None:
                continue

            item_id = self._get_id(item)
            if item_id in self._seen:
                continue

            self._seen.add(item_id)
            yield self._transform_cached(item)

    def _transform_cached(self, item: Data) -> ProcessedData:
        """Cache transforms since prototype showed this is expensive."""
        if item not in self._transform_cache:
            self._transform_cache[item] = transform(item)
        return self._transform_cache[item]
```

## Remember: The Wisdom of Experience

Brooks wrote: "Plan to throw one away; you will, anyhow." This isn't permission to be sloppy - it's recognition that **learning is an essential part of building something new**.

The OS/360 project that Brooks managed was massive, complex, and groundbreaking. Despite careful planning by brilliant engineers, they still had to learn by doing. If Brooks' team at IBM needed to learn through building, so do we.

The various techniques and disciplines gathered around the banner of "agile" are on balance more honest at facing up to this unavoidable tension between planning and learning. "Build one to throw away" is the recognition that:

- **Planning has limits** - You can't anticipate everything
- **Experience teaches** - Building reveals truths that thinking can't
- **Learning is valuable** - Even if the code is discarded
- **Better the second time** - Knowledge compounds with each iteration

**The code is temporary. The learning is permanent.**

Apply this principle with Brooks' own wisdom: use it when genuinely exploring the unknown, capture the learning rigorously, and build the real system with confidence earned through experience.

---

## References

- Brooks, Frederick P. "The Mythical Man-Month: Essays on Software Engineering" (1975, Anniversary Edition 1995)
- Brooks' reflection: "The Mythical Man-Month after 20 Years" (1995)
- Chapter 11: "Plan to Throw One Away" (original text)

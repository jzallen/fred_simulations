# Anti-Patterns to Avoid

## When to read this

Read this document to understand:
- Common pitfalls when applying "build one to throw away"
- How to recognize when you're falling into these traps
- Solutions and mitigation strategies for each anti-pattern
- Real-world consequences of these mistakes

---

## Overview

While "build one to throw away" is a powerful methodology, there are several ways to misapply it that turn a learning exercise into wasted effort. These anti-patterns can undermine the entire approach and lead to worse outcomes than not prototyping at all.

---

## ❌ Anti-Pattern 1: "We'll just clean up the prototype"

### The Problem

Users can become confused between prototype and finished system, leading to expectations that the prototype can simply be polished into production code. Stakeholders without technical background may try to convince you to reuse the source code from the prototype, believing it will shorten the time required to release the product.

### Why This Fails

The technical debt and architectural compromises baked into the prototype make this path **more expensive** than rebuilding from scratch. The prototype was built with speed as the only priority - it lacks:
- Proper error handling
- Security considerations
- Scalability
- Maintainability
- Clean architecture
- Comprehensive testing
- Documentation

### Real Consequences

Attempting to productionize a prototype leads to:
- Months of "cleanup" that turns into complete rewrites
- Compounding technical debt
- Brittle, hard-to-maintain code
- Security vulnerabilities
- Performance issues at scale
- Delayed shipment dates (not faster delivery)

### Solution

**Make the throwaway status explicit and enforced:**

1. **Use a separate directory:** `throwaway-prototype/` (not `prototype/`)
2. **Use a different language if possible:** Prevents code reuse temptation
3. **Add warning comments everywhere:** `# THROWAWAY - DO NOT USE IN PRODUCTION`
4. **Archive it when done:** Move to `archive/` to prevent access
5. **Communicate clearly:** Set expectations with stakeholders upfront

**Template README for throwaway:**
```markdown
# ⚠️ THROWAWAY PROTOTYPE - DO NOT USE IN PRODUCTION

This code will be DELETED on [date].
Purpose: Learn [specific things]
Will be rebuilt properly using learnings captured in LEARNINGS.md
```

---

## ❌ Anti-Pattern 2: "Second-system effect"

### The Problem

Don't try to add every feature you thought of during the prototype. The second system effect occurs when you try to build a bigger, shinier, more complex system than the first one without the proper knowledge - there are many features that did not fit in the first project and were pushed into the second version.

### Why This Fails

This usually leads to:
- Overly complex systems
- Over-engineered solutions
- Feature creep
- Delayed delivery
- Systems that are harder to maintain than they should be
- Loss of focus on core requirements

### The Brooks Warning

Brooks identified this as a common pitfall where teams, emboldened by the success of their prototype, attempt to build a "kitchen sink" system that includes everything they dreamed of.

### Solution

**Build the second version to the same scope with better implementation.**

Keep a disciplined approach:
1. **Stick to the original scope:** Only build what was validated
2. **Track "nice to have" separately:** Maintain a backlog for future iterations
3. **Focus on quality, not quantity:** Better implementation of the same features
4. **Resist scope creep:** Just because you learned about feature X doesn't mean you must build it now

**Decision framework:**
- Was this feature in the original requirements? → Build it
- Did the prototype reveal this is essential? → Build it
- Is this a "nice to have" we thought of? → Defer to later

---

## ❌ Anti-Pattern 3: "Plan to throw one away... and throw away two"

### The Problem

Brooks later warned that if you do indeed plan to throw one away, you'll end up throwing away two. This happens when:
- You assign the throwaway version to a mediocre programmer and switch programmers for "the real thing"
- The learning from the throwaway doesn't transfer to the real implementation
- Management pressure causes premature productionization of prototype code
- Different teams build the prototype vs. the production system

### Why This Fails

The learning is lost when:
- The person who gained the insights doesn't build the production version
- Knowledge isn't properly documented and transferred
- The production team repeats mistakes already discovered
- The production system encounters the same pitfalls the prototype revealed

### Real Consequences

You end up with:
- Two throwaway systems instead of one
- Doubled learning time
- Repeated mistakes
- Lost investment in the first prototype
- Demoralized team members

### Solution

**The same person/team who builds the throwaway should build the real system, bringing their hard-won insights with them.**

Best practices:
1. **Same team throughout:** Don't switch developers between phases
2. **Rigorous knowledge capture:** Document learnings daily
3. **Knowledge transfer if necessary:** Pair programming, extensive documentation
4. **Resist pressure to rush:** Allow time for proper rebuild
5. **Make learning transfer explicit:** Review learnings before starting production build

**Knowledge transfer checklist:**
- [ ] All discoveries documented in learning log
- [ ] Test cases written for all edge cases
- [ ] ADRs created for architectural decisions
- [ ] Complexity hotspots identified and documented
- [ ] Production team has reviewed all learnings
- [ ] Q&A session held between prototype and production teams

---

## ❌ Anti-Pattern 4: "Perfect prototype"

### The Problem

A key property of prototyping is that it's supposed to be done quickly. If developers lose sight of this fact, they very well may try to develop a prototype that is too complex. When the prototype is thrown away, the precisely developed requirements that it provides may not yield a sufficient increase in productivity to make up for the time spent developing the prototype.

### Why This Fails

Spending too much time making the prototype production-quality defeats the purpose:
- The learning could have been gained faster with a rougher prototype
- Time spent on polish doesn't teach you anything
- The "sunk cost fallacy" makes it harder to throw away
- Stakeholders are more likely to want to keep "high quality" code

### Warning Signs

You're building a "perfect prototype" if:
- Spending time on code formatting and style
- Writing comprehensive tests (beyond learning tests)
- Implementing complete error handling
- Adding logging and monitoring
- Writing extensive documentation
- Optimizing performance
- Considering edge cases beyond core learning
- Taking more than 40% of estimated production build time

### Solution

**Time-box the prototype and focus ruthlessly on learning.**

Discipline techniques:
1. **Set a strict deadline:** 2-3 days for most prototypes
2. **Define learning goals upfront:** Stop when they're answered
3. **Skip anything that doesn't teach:** If it's not about learning, don't do it
4. **Use "good enough" approaches:** Not "best practice" approaches
5. **Embrace technical debt:** You're throwing it away anyway

**Prototype checklist:**
- [ ] Does this teach me something? → Do it
- [ ] Is this just polish? → Skip it
- [ ] Will this take more than a few hours? → Find a simpler approach
- [ ] Am I following best practices? → You're doing it wrong (for a prototype)

---

## ❌ Anti-Pattern 5: "Documentation-free throwaway"

### The Problem

If team members don't make a record of the work on time, others will not know about the change and the latest process of the project, thus the team may have to spend lots of time to re-communicate or re-do the work.

### Why This Fails

While the code is throwaway, **the learnings must be captured**. Without documentation:
- Insights are lost when memory fades
- Different team members have different understandings
- Can't justify architectural decisions later
- Production build repeats prototype mistakes
- Can't demonstrate value of prototype to stakeholders

### Real Consequences

Months later when asked "why did we choose this architecture?":
- "I think the prototype showed... but I don't remember exactly"
- "We tried something else first but it didn't work... I forget why"
- "There was a good reason for this... let me try to remember"

### Solution

**Document learnings continuously, not at the end.**

Documentation discipline:
1. **Daily learning log:** Write discoveries as you make them
2. **ADRs for decisions:** Document why, not just what
3. **Tests as specification:** Every edge case becomes a test
4. **Photos/screenshots:** Capture visual learnings
5. **Code comments for insights:** `# Tried X, failed because Y`

**Minimum viable documentation:**
- `README.md`: Purpose, timeline, status
- `LEARNINGS.md`: Daily log of discoveries
- `TESTS.md`: Edge cases and requirements discovered
- `DECISIONS.md`: Key architectural choices and why

**Learning log template:**
```markdown
# Learning Log - [Project Name]

## [Date]
### Discoveries
- [What you learned]

### What Worked
- [Successful approaches]

### What Failed
- [Failed approaches and why]

### For Production Build
- [Decisions informed by today's learning]
```

---

## Recognizing Anti-Patterns Early

### Warning Signs Checklist

You may be falling into anti-patterns if:

- [ ] Stakeholders are asking "can we just ship the prototype?"
- [ ] You're spending time on code quality in the throwaway
- [ ] The prototype is taking longer than planned
- [ ] You're adding features beyond the learning goals
- [ ] Different people are building prototype vs. production
- [ ] You haven't documented any learnings yet
- [ ] You're building features "while you're at it"
- [ ] The prototype is in the main codebase
- [ ] You're writing comprehensive tests for the prototype
- [ ] You can't remember what you learned two days ago

### Recovery Strategies

If you recognize an anti-pattern:

1. **Stop and reassess:** What's the learning goal? Are you still focused on it?
2. **Review learnings to date:** What have you discovered? Document it now.
3. **Re-establish boundaries:** Make throwaway status explicit
4. **Communicate with stakeholders:** Reset expectations
5. **Time-box remaining work:** Set a firm deadline to finish
6. **Extract learnings immediately:** Don't wait until the end

---

## The Balance

The art of "build one to throw away" is finding the balance between:
- **Too rough:** Doesn't teach you enough → Wasted effort
- **Too polished:** Takes too long → Wasted effort
- **Just right:** Fast enough to be cheap, thorough enough to teach

**The goal is learning, not building.** When you've learned enough, stop and move to Phase 2 (extract learnings).

---

## Success Pattern (For Contrast)

A successful "build one to throw away" approach:

✅ Takes 20-40% of production build time
✅ Clearly marked as throwaway from day one
✅ Focused on specific learning goals
✅ Daily documentation of discoveries
✅ Same team builds prototype and production
✅ Tests capture all edge cases found
✅ ADRs document key decisions
✅ No pressure to productionize prototype
✅ Scoped to original requirements (no feature creep)
✅ Archived when complete, learnings preserved

---

## Remember

**Avoiding these anti-patterns is as important as following the methodology itself.**

The anti-patterns often feel like "efficiency" or "pragmatism" in the moment:
- "We've already built it, let's just use it" (feels efficient, costs more later)
- "Let's add this feature while we're here" (feels pragmatic, adds complexity)
- "We don't need to document, we'll remember" (feels fast, loses knowledge)

Resist these temptations. Trust the process. **The code is temporary. The learning is permanent.**

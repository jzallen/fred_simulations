# Historical Context: Build One to Throw Away

## When to read this

Read this document when you want to understand:
- The origins of the "build one to throw away" principle
- Why Fred Brooks advocated for this approach
- How the principle has evolved over time
- The cultural and organizational implications

---

## The Origins: Fred Brooks and The Mythical Man-Month

This principle comes from Frederick Brooks' seminal 1975 book "The Mythical Man-Month: Essays on Software Engineering," based on his experiences managing IBM's OS/360 project in the 1960s. Brooks observed that complex software projects rarely get their fundamental design right on the first attempt, no matter how carefully planned.

**Brooks' original statement:**
> "Where a new system concept or new technology is used, one has to build a system to throw away, for even the best planning is not so omniscient as to get it right the first time. Hence plan to throw one away; you will, anyhow."

### The OS/360 Project

The OS/360 project was one of the largest software projects of its era, and Brooks witnessed firsthand how even the most experienced teams couldn't anticipate all the complexities and interactions in a large system until they had actually built something.

Key insights from the OS/360 experience:
- Complex systems have emergent properties that can't be predicted through planning alone
- Even brilliant engineers can't anticipate all interactions in a large system
- The act of building reveals truths that thinking and planning cannot
- Early iteration and learning prevent larger problems later

This principle highlights the importance of early iteration and learning, even if it means discarding initial efforts.

---

## Brooks' Later Refinement

In the 1995 anniversary edition of The Mythical Man-Month, Brooks reflected on this principle and wrote:

> "This I now perceive to be wrong, not because it is too radical, but because it is too simplistic. The biggest mistake in the 'Build one to throw away' concept is that it implicitly assumes the classical sequential or waterfall model of software construction."

### The Evolution of Understanding

Brooks clarified that his original advice was meant for the waterfall development era, where teams would plan everything upfront and then build it all at once. In modern iterative development, we continuously refactor and rebuild - but we do it incrementally rather than throwing away an entire system.

**The key insight remains valid:** You learn by building, and your first attempt at solving a novel problem will reveal insights you couldn't have anticipated through planning alone.

### The Enduring Truth

Despite the evolution of software development practices, the core principle persists because it addresses a fundamental limitation: **programmers aren't smart enough to get the core design choices right until they've built something that works.**

---

## Modern Interpretation

Building a prototype or initial version that is expected to be thrown away can be seen as a form of risk management - it allows teams to identify and address major issues early when they are less costly and easier to fix.

### Contemporary Applications

Today, "build one to throw away" is best applied as:
- **Rapid throwaway prototypes** for exploring specific unknowns
- **Spike solutions** in Agile development for investigating technical questions
- **Proof-of-concept code** to validate feasibility before committing to a design
- **Learning exercises** when entering unfamiliar technical territory

### Evolution Alongside Agile

The concept evolved alongside software engineering practices from waterfall to Agile, but the core truth endures. The various techniques and disciplines gathered around the banner of "agile" are on balance more honest at facing up to this unavoidable tension between planning and learning.

### When the Principle Doesn't Apply

**Brooks' Caveat:**
> "If you've just written three driver-scheduling systems or foreign-exchange systems in a row, you'll probably go into the fourth with a pretty good grasp of what's important. Those kinds of systems matter. But the interesting software is by definition the stuff that isn't the fourth iteration of anything."

The principle is for **new, novel work** - not for repeating familiar patterns.

---

## The Cultural Challenge

Embracing the "build one to throw away" philosophy requires a cultural shift in many organizations. It necessitates valuing learning and long-term project success over short-term efficiencies and outputs.

### The Tension Brooks Identified

There's a terrible glaring conflict between what sensible managers want and what sensible programmers know:

**Managers want:**
- A plan they can rely on
- Locked-in design constraints
- Work that can be dealt out and tracked
- Promises that can be kept
- Predictable progress

**Programmers know:**
- They're not smart enough to get core design choices right initially
- Building reveals essential truths
- Learning comes through doing
- The first attempt will have flaws
- Experience compounds with iteration

The "build one to throw away" approach acknowledges this fundamental tension and provides a structured way to balance learning with delivery.

### Cultural Shifts Required

**For teams:**
- Foster a culture that views the initial development phase as a learning experience rather than just a product-building exercise
- Make throwaway status explicit in project naming and documentation
- Celebrate learning outcomes, not just working code
- Resist pressure to productionize prototypes
- Help align everyone's expectations and justify the need for early iterations

**For management:**
- Understand that initial "waste" prevents larger waste later
- Budget for learning iterations on novel projects
- Balance this approach with practical constraints like budgets and deadlines
- Trust that experienced teams will rebuild faster and better
- Value the reduction of risk and uncertainty

### The Investment Mindset

Building a throwaway prototype is not waste - it's an investment in:
- **Risk reduction:** Identifying problems when they're cheap to fix
- **Knowledge creation:** Building technical capital in your team
- **Better estimates:** Making predictions based on actual experience
- **Faster delivery:** The real build proceeds more quickly with validated assumptions
- **Higher quality:** Avoiding architectural mistakes that would require expensive refactoring

---

## The Wisdom of Experience

Brooks wrote: "Plan to throw one away; you will, anyhow." This isn't permission to be sloppy - it's recognition that **learning is an essential part of building something new**.

The OS/360 project that Brooks managed was massive, complex, and groundbreaking. Despite careful planning by brilliant engineers, they still had to learn by doing. If Brooks' team at IBM needed to learn through building, so do we.

### Core Principles

The "build one to throw away" recognition acknowledges that:

- **Planning has limits** - You can't anticipate everything
- **Experience teaches** - Building reveals truths that thinking can't
- **Learning is valuable** - Even if the code is discarded
- **Better the second time** - Knowledge compounds with each iteration

### The Ultimate Truth

**The code is temporary. The learning is permanent.**

Apply this principle with Brooks' own wisdom: use it when genuinely exploring the unknown, capture the learning rigorously, and build the real system with confidence earned through experience.

---

## References

- Brooks, Frederick P. "The Mythical Man-Month: Essays on Software Engineering" (1975, Anniversary Edition 1995)
- Brooks' reflection: "The Mythical Man-Month after 20 Years" (1995)
- Chapter 11: "Plan to Throw One Away" (original text)

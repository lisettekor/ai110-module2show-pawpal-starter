# PawPal+ Project Reflection

## 1. System Design

**Core user actions**

A PawPal+ user should be able to:

1. **Add a pet and its care tasks** — record the pet (name, species) and the tasks it needs (title, duration, priority, fixed time, notes).
2. **Generate a prioritized daily plan** — given how much available time the owner has today, produce a schedule with real clock times that fits the most important tasks first.
3. **Explain rationale for the plan** — read which tasks were scheduled, when, and the reason, plus which tasks were skipped because time ran out.

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

My initial UML was a simple class diagram with four classes arranged in an ownership chain, plus one class holding the scheduling logic.

Owner — represents the person planning care. Responsible for holding the owner's daily time budget (available_minutes) and preferences, and for managing the list of pets (add_pet, set_preference).

Pet — represents an animal being cared for (name, species, age). Responsible for owning and managing its own list of care tasks (add_task, remove_task, get_tasks).

Task — represents a single unit of care (title, duration, priority, category). Its main responsibility is knowing how it should be ordered relative to other tasks (sort_key).

Scheduler — the "brain" of the system. Responsible for turning a set of tasks plus the owner's time constraint into a timed daily plan: sorting by priority (_sort_tasks), dropping lowest-priority tasks that don't fit the budget (_fit_to_budget), assigning clock times (_assign_times), and explaining the result (explain).

The relationships were a one-to-many ownership chain — an Owner has many Pets, and a Pet has many Tasks — while the Scheduler depends on both Tasks and the Owner's constraints without owning them. I deliberately separated the data classes (Owner, Pet, Task) from the behavior class (Scheduler) so the scheduling logic would be easy to test in isolation.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.


I cut recurrence to keep v1 simple, then added it back as frequency once I realized daily-vs-weekly was core to the pet-care scenario, and added a completed flag so finished tasks drop out of the plan.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

My scheduler considers four constraints, applied as a pipeline in generate_plan:

1. **Due day + completion status** (is_due, completed) — decides which tasks are even candidates today. A task is skipped if it isn't due on the planned day (daily / weekly / weekdays / weekends) or is already done.
2. **Priority** (high/medium/low, with duration as a tie-breaker) — decides the order tasks are considered in.
3. **Time budget** (available_minutes) — the hard cap on how much fits.
4. **Fixed clock time** (preferred_time) — pins certain tasks (e.g. meds at 08:00) to an exact time instead of letting them float.

I treated the **time budget as the hard constraint** because it maps to something real — the owner only has so many hours — so it's the gate that decides how much gets done. **Priority** is the next most important, because when time runs short the whole point is to sacrifice the least-important tasks first. Due-day and completion come *before* both of those (they decide candidacy), and duration is only a tie-breaker within a priority level.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

_fit_to_budget stops at the first task that doesn't fit rather than skipping it to squeeze in a smaller later task. That keeps the rule simple and strictly priority-respecting (never skip a medium task to fit a low one), at the cost of occasionally leaving a few minutes unused. Reasonable for pet care, where honoring priority matters more than packing the schedule tight.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

> _Draft based on this session — rewrite in your own words:_

I used AI mainly to extend and refine the logic layer after the initial design: adding recurrence, filtering, time-based sorting, and conflict detection, then documenting the tradeoffs. The most helpful prompts were **specific and incremental** ("add filtering by pet/status," "detect conflicts across pets," "simplify for readability/performance") rather than "build the whole thing" — each one produced a change small enough for me to actually read and check. Asking "are there algorithms that can be simplified?" was useful because it surfaced a hidden O(n²) I hadn't noticed.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

> _Draft based on this session — rewrite in your own words:_

Two moments stand out. First, the AI's conflict-warning code used emoji (⚠️/✅), which **crashed the program** on my Windows terminal (cp1252 can't encode them) — ironic for a feature meant to "warn instead of crash." I caught it by actually running main.py, and we replaced the emoji with plain ASCII. Second, when asked to document a tradeoff, the prompt suggested an example ("only checking exact time matches") that **wasn't true of my code** — my detect_conflicts already checks full-duration overlap — so I documented the real tradeoff (the greedy budget cut) instead. I verified suggestions by running the test suite (22 tests) and the demo after every change, rather than trusting that the code was correct because it looked reasonable.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

I have 22 tests in tests/test_pawpal.py covering the logic layer:

- **Task basics** — marking a task done flips its status; adding a task grows the pet's list.
- **Recurrence (is_due)** — daily is due every day, weekly only on listed days, weekdays/weekends match the right group, and an unknown frequency is never due.
- **Filtering (filter_tasks)** — by pet name, by completion status, and the two combined.
- **Sorting by time (sort_by_time)** — pinned tasks come out in clock order and untimed tasks fall to the back.
- **Conflict detection** — a same-pet double-booking is flagged as same_pet, a clash across two pets is flagged as cross-pet, and back-to-back tasks don't count as a conflict.
- **Lightweight warning (check_conflicts)** — returns an empty string when clean, a warning message on an overlap, and — importantly — a warning *instead of crashing* when a clock time is malformed.
- **Recurrence regeneration** — completing a daily task auto-queues a fresh pending copy; a non-recurring task queues nothing.

These mattered because the scheduler is a pipeline where each stage feeds the next (filter → sort → budget → place), so a bug in one stage silently corrupts the plan. Testing each rule in isolation makes it obvious *which* stage broke.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I'm fairly confident in the core pipeline — the happy path and the main rules are all covered, and the demo in main.py exercises them end to end. The conflict-detection and recurrence features are the newest, so those are where I'd want more coverage.

Edge cases I'd test next:
- **Budget of exactly 0**, and a single task longer than the whole budget (nothing should schedule).
- **A pinned preferred_time that falls before start_time**, or two flexible tasks whose stacking pushes past midnight.
- **Real date-based recurrence** — right now "next occurrence" reuses the same weekday model rather than an actual calendar date (timedelta), so a daily task's "next day" isn't a true date yet.
- **A task belonging to no pet** passed to complete_task (currently marked done but silently not re-queued).

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

> _Draft based on this session — rewrite in your own words:_

I'm most satisfied with the clean separation between the data classes (Owner/Pet/Task) and the Scheduler. Because the logic was isolated, I could keep adding features — recurrence, filtering, conflict detection — as small, independently testable methods without the classes tangling together. The generate_plan pipeline (filter → sort → budget → place) stayed readable even as it grew.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

> _Draft based on this session — rewrite in your own words:_

I'd make the model **date-aware** instead of using weekday-name strings. Right now "next occurrence" of a daily task can't produce a real calendar date (it would need datetime/timedelta), which limits recurrence. I'd also make the scheduler **resolve** conflicts, not just report them — currently a pinned task is always placed even if it collides, and detect_conflicts only warns after the fact.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

> _Draft based on this session — rewrite in your own words:_

Separating data from behavior early paid off the most — it's what let the system grow without rewrites. On the AI side, the key lesson was that **running the code is the real check**: the most convincing-looking suggestion (the emoji warning) was the one that crashed, and I only caught it by executing it, not by reading it.

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

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

_fit_to_budget stops at the first task that doesn't fit rather than skipping it to squeeze in a smaller later task. That keeps the rule simple and strictly priority-respecting (never skip a medium task to fit a low one), at the cost of occasionally leaving a few minutes unused. Reasonable for pet care, where honoring priority matters more than packing the schedule tight.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

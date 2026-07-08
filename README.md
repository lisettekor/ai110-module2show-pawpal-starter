# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## ✨ Features

The scheduling logic in `pawpal_system.py` implements the following algorithms (see [Smarter Scheduling](#-smarter-scheduling) for details):

- **Priority-based planning** — tasks are sorted highest priority first (ties broken by shorter duration), so the most important care happens even when time is tight.
- **Time-budget fitting** — greedily keeps the highest-priority tasks that fit the owner's available minutes and drops the rest, so a plan never exceeds the day's time budget.
- **Sorting by time** — pinned tasks with a fixed `preferred_time` (e.g. meds at `14:00`) are placed in chronological clock order; flexible tasks fill the gaps around them.
- **Clock-time assignment** — each kept task is given a concrete start/end window, with a running cursor so back-to-back tasks stack cleanly and a long pinned task pushes later ones forward.
- **Daily & weekly recurrence** — tasks recur `daily`, `weekly` (on chosen days), `weekdays` (Mon–Fri), or `weekends` (Sat/Sun); the scheduler plans only tasks due on the chosen day.
- **Auto-regeneration on completion** — marking a recurring task complete automatically queues a fresh pending copy on the same pet, so it reappears on its next due day.
- **Conflict detection** — every pair of scheduled items is checked for overlapping time windows, distinguishing a single pet's double-booking from a clash across two pets.
- **Conflict warnings** — a non-crashing check produces a plain-text warning (or an empty string when clean) safe to display directly in the UI.
- **Filtering** — tasks can be narrowed by pet, completion status, and/or category in any combination.
- **Plan explanation** — the scheduler produces a human-readable summary of what was scheduled, what was skipped, and any conflicts.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
# e.g.:
# Daily plan for Biscuit (Golden Retriever):
#   08:00 — Morning walk (30 min) [priority: high]
#   09:00 — Feeding (10 min) [priority: high]
#   ...
```
```
================================================
PawPal+ demo — owner: Jordan
Pets: Biscuit, Mochi
Time available today: 90 min
================================================

Today's Schedule
------------------------------------------------
Plan for Jordan (Mon):
  08:00–08:05  Feeding (5 min) [priority: high]
  08:05–08:15  Feeding (10 min) [priority: high]
  08:15–08:45  Morning walk (30 min) [priority: high]
  08:45–08:55  Clean litter (10 min) [priority: medium]
  08:55–09:15  Training (20 min) [priority: medium]
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
$ pytest -q
.........................                                                [100%]
25 passed in 0.06s
```

### What the tests cover

The suite in `tests/test_pawpal.py` (25 tests) exercises every behavior in the logic layer:

- **Task & Pet basics** — `mark_done()` flips a task's `completed` flag; adding a task grows the pet's task list.
- **Recurrence rules (`is_due`)** — daily tasks are due every day, weekly tasks only on their listed days, and the `weekdays`/`weekends` shortcuts match the right days; unknown frequencies are never due.
- **Filtering (`Owner.filter_tasks`)** — narrowing by pet name, by completion status, and by pet + category combined.
- **Sorting** — `sort_by_time()` puts pinned tasks first in clock order (untimed tasks last), and a full `generate_plan()` emits its items in chronological start-time order.
- **Conflict detection** — two tasks at the exact same time flag one conflict; overlapping pinned tasks are detected and labeled same-pet vs. cross-pet; back-to-back tasks do **not** conflict; `check_conflicts()` returns `""` when clean, a `WARNING…` string on overlap, and warns instead of crashing on a malformed clock time.
- **Recurrence regeneration** — `next_occurrence()` returns a fresh pending copy (with an independent `days_of_week` list) for recurring tasks and `None` for one-offs; completing a daily task queues a new pending instance on the same pet, due the following day, while completing a one-off queues nothing.

## 📐 Smarter Scheduling

Beyond the basic "sort by priority and fill the time budget" plan, PawPal+ implements four smarter scheduling behaviors. All of them live in the logic layer (`pawpal_system.py`) so they can be tested without the UI.

| Feature | Implementing method(s) | What it does |
|---------|------------------------|--------------|
| **Sorting by time** | `Scheduler.sort_by_time()` → `Task.time_key()` | Orders tasks by fixed clock time |
| **Filtering** | `Owner.filter_tasks()` | Narrows tasks by pet, completion status, or category |
| **Conflict detection** | `Scheduler.detect_conflicts()`, `Scheduler.check_conflicts()`, `Conflict` | Finds overlapping time windows (same-pet vs. cross-pet) |
| **Recurring tasks** | `Task.is_due()`, `Task.next_occurrence()`, `Scheduler.complete_task()` | Decides due days and regenerates tasks on completion |

### Sorting behavior

`Scheduler.sort_by_time(tasks)` returns tasks in clock order by delegating to `Task.time_key()`. Tasks with a fixed `preferred_time` (e.g. meds at `"08:00"`) sort first in ascending time order; untimed ("flexible") tasks fall to the back. Because Python's `sorted` is stable, flexible tasks keep whatever order the caller gave them (e.g. priority order), so pinned appointments land on the clock and everything else fills the gaps around them.

### Filtering behavior

`Owner.filter_tasks(*, pet=None, completed=None, category=None)` returns the owner's tasks narrowed by any combination of keyword filters:

```python
owner.filter_tasks(completed=False)               # only pending tasks
owner.filter_tasks(pet="Mochi")                    # only Mochi's tasks
owner.filter_tasks(pet="Mochi", completed=False)   # both filters combined
```

Passing `None` for a filter means "don't filter on this," so the filters compose cleanly. `pet` accepts either a `Pet` object or a name string.

### Conflict detection logic

`Scheduler.detect_conflicts()` compares every pair of scheduled items and returns a list of `Conflict` objects for any whose clock windows overlap — using a true interval-overlap test (`a_start < b_end and b_start < a_end`), not just exact start-time matches. Each `Conflict` records the owning pet of both tasks, so its `same_pet` property distinguishes a single pet's double-booking from a clash across two pets, and its `scope` property produces the human-readable label (e.g. `"Mochi vs Biscuit"`).

`Scheduler.check_conflicts()` is a lightweight companion that returns a plain warning **string** (empty when clean) instead of structured data, and is wrapped so a malformed clock time can never crash the caller — it degrades to a `"WARNING: could not check for conflicts…"` message.

### Recurring task logic

Recurrence is handled in three cooperating pieces:

- `Task.is_due(day)` decides whether a task should happen on a given day, supporting `"daily"`, `"weekly"` (via `days_of_week`), `"weekdays"` (Mon–Fri), and `"weekends"` (Sat/Sun). Unknown frequencies are treated as never due.
- `Task.next_occurrence()` builds a fresh, uncompleted copy of a recurring task (with an independent `days_of_week` list) for its next run, or returns `None` for a one-off task.
- `Scheduler.complete_task(task)` ties them together: it marks the task done and, if it recurs, auto-queues the new instance onto the same pet so the task reappears on its next due day.

## 📸 Demo Walkthrough

Launch the app with `streamlit run app.py`, then follow along:

1. **Set the owner & day.** Enter the owner's name, the total time available for the day (in minutes), the day being planned, and the start time (`HH:MM`). These become the scheduler's constraints. The owner is kept in session state, so pets and tasks persist as you interact.
2. **Add one or more pets.** Give each a name, species, and age, then click **Add pet**. Until at least one pet exists, the app prompts you to add one before scheduling tasks.
3. **Add care tasks to a pet.** Pick which pet the task belongs to, then set its description, duration, priority, and frequency (`daily`, or `weekly` with specific days). Click **Add task** — each pet's current tasks appear in a table below.
4. **Generate the schedule.** Click **Generate schedule**. The scheduler filters to tasks due on the chosen day (and not completed), **sorts** by priority, drops the lowest-priority tasks that don't fit the time budget, and assigns clock times. Pinned `preferred_time` tasks land on the clock; flexible tasks fill the gaps. The result shows as a start/end timetable with summary metrics (scheduled, skipped, minutes used/free).
5. **Review conflicts, dropped tasks, and the reasoning.** Overlapping time windows are surfaced as **conflict warnings** (labeled same-pet double-booking vs. cross-pet clash); tasks skipped for lack of time are listed under "Skipped (ran out of time)"; and the **"Why this plan?"** expander shows the scheduler's full text explanation.
6. **Start over.** Click **Start over (clear owner & pets)** to reset the session and begin fresh.

### Example workflow

A concrete run — owner *Jordan* with 90 minutes, planning **Mon**:

1. Add pet **Biscuit** (dog), then add **Mochi** (cat).
2. Give Biscuit a `high`-priority *Vet call* pinned to `08:00` and a *Morning walk*; give Mochi some *Meds* also pinned to `08:00`.
3. Click **Generate schedule** → the timetable fills from `08:00`, the two `08:00` tasks raise a **cross-pet conflict warning**, and the lowest-priority task that doesn't fit the 90-minute budget is dropped.
4. Open **"Why this plan?"** to see the scheduled tasks, the skipped one, and the conflict spelled out.

### Sample CLI output (`python main.py`)

The same logic layer can be driven headless via `main.py`, which prints the sorting, filtering, schedule, and conflict-warning demos:

```text
================================================
PawPal+ demo — owner: Jordan
Pets: Biscuit, Mochi
Time available today: 90 min
================================================

Same tasks after Scheduler.sort_by_time()
------------------------------------------------
  [08:00] Vet call
  [08:00] Meds
  [(flexible)] Morning walk
  [(flexible)] Training
  ...

Filtering demo — Owner.filter_tasks()
------------------------------------------------
Done (completed=True):     ['Feeding']
Mochi's tasks (pet='Mochi'): ['Clean litter', 'Feeding', 'Meds', 'Weekly brush']

Today's Schedule
------------------------------------------------
Plan for Jordan (Mon):
  08:00–08:10  Meds (10 min) [priority: high]
  08:00–08:20  Vet call (20 min) [priority: high]
  08:20–08:25  Feeding (5 min) [priority: high]
  08:25–08:55  Morning walk (30 min) [priority: high]
  08:55–09:05  Clean litter (10 min) [priority: medium]
Skipped (ran out of time):
  - Training (20 min) [priority: medium]
Conflicts (overlapping times):
  - [Mochi vs Biscuit] Meds (08:00–08:10) overlaps Vet call (08:00–08:20)

Conflict warning
------------------------------------------------
WARNING: 1 scheduling conflict: Meds (08:00) overlaps Vet call (08:00) [Mochi vs Biscuit]
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

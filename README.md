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
# Paste your pytest output here
```

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

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

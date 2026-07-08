"""PawPal+ logic layer.

All backend domain classes live here: Task, Pet, Owner, Scheduler, plus the
small ScheduledItem value type the plan is made of. Data-holder objects use
dataclasses.

Design decisions (from the UML brainstorm):
  * The plan assigns clock times, starting at Scheduler.start_time.
  * When tasks exceed the time budget, keep the highest-priority tasks and
    stop at the first task that doesn't fit (dropping it and the rest).
  * Tasks recur daily or weekly; the scheduler plans one named day and skips
    tasks that aren't due that day or are already completed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

# Lower rank sorts first, so "high" comes before "low". Unknown priorities
# fall to the back rather than sorting alphabetically (the string-sort trap).
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}

# Weekday groups used by the "weekdays"/"weekends" recurrence shortcuts. Kept
# lowercase so day matching is case-insensitive.
_WEEKDAYS = {"mon", "tue", "wed", "thu", "fri"}
_WEEKENDS = {"sat", "sun"}

# Frequencies that repeat, so completing one should queue a fresh instance.
_RECURRING = {"daily", "weekly", "weekdays", "weekends"}


def _priority_rank(priority: str) -> int:
    """Map a priority label to a sortable rank (unknown -> last)."""
    return _PRIORITY_RANK.get(priority.lower(), len(_PRIORITY_RANK))


def _to_minutes(clock: str) -> int:
    """Convert a "HH:MM" clock string to minutes since midnight."""
    hours, minutes = clock.split(":")
    return int(hours) * 60 + int(minutes)


def _to_clock(minutes: int) -> str:
    """Convert minutes since midnight back to a "HH:MM" clock string."""
    return f"{(minutes // 60) % 24:02d}:{minutes % 60:02d}"


@dataclass
class Task:
    """One care activity (a walk, a feeding, meds, etc.).

    Attributes:
        description: Human-readable name, e.g. "Morning walk".
        duration_minutes: How long the task takes, in minutes.
        priority: One of "low", "medium", "high".
        frequency: How often the task recurs: "daily" or "weekly".
        days_of_week: For weekly tasks, the days it happens, e.g.
            ["Mon", "Thu"]. Ignored when frequency is "daily".
        completed: Whether the task is already done (skipped when planning).
        category: Kind of task, e.g. "walk", "feeding", "meds", "grooming".
        preferred_time: Optional fixed clock time "HH:MM" the task must start
            at (e.g. meds at "14:00"). When set, the scheduler pins the task
            there instead of stacking it after the previous one.
    """

    description: str
    duration_minutes: int
    priority: str = "medium"
    frequency: str = "daily"
    days_of_week: list[str] = field(default_factory=list)
    completed: bool = False
    category: str = "other"
    preferred_time: str | None = None

    def sort_key(self) -> tuple:
        """Sort key ranking by priority first, then shorter duration."""
        return (_priority_rank(self.priority), self.duration_minutes)

    def time_key(self) -> tuple:
        """Sort key placing timed tasks in clock order, untimed tasks last.

        Tasks with a ``preferred_time`` sort ahead (group 0) ordered by that
        time; tasks without one fall to the back (group 1) so they fill the
        gaps around the pinned tasks.
        """
        if self.preferred_time:
            return (0, _to_minutes(self.preferred_time))
        return (1, 0)

    def is_due(self, day: str) -> bool:
        """Return True if this task should happen on the given day.

        Supported ``frequency`` values:
          * "daily"    — every day.
          * "weekly"   — only the weekdays listed in ``days_of_week``.
          * "weekdays" — Monday through Friday.
          * "weekends" — Saturday and Sunday.
        Any other value is treated as "never due".
        """
        freq = self.frequency.lower()
        d = day.lower()
        if freq == "daily":
            return True
        if freq == "weekly":
            return d in {x.lower() for x in self.days_of_week}
        if freq == "weekdays":
            return d in _WEEKDAYS
        if freq == "weekends":
            return d in _WEEKENDS
        return False

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def next_occurrence(self) -> Task | None:
        """Return a fresh, uncompleted copy of this task for its next run.

        Recurring tasks (daily / weekly / weekdays / weekends) come back, so
        completing one should leave a new pending instance behind. Returns a
        new Task with ``completed`` reset to False and an independent
        ``days_of_week`` list (so editing one occurrence can't mutate the
        other). One-off or unknown-frequency tasks return None — nothing to
        regenerate.

        This only *builds* the next instance; it does not attach it anywhere,
        since a Task has no reference to its owning Pet. See
        :meth:`Scheduler.complete_task`, which wires the new instance in.
        """
        if self.frequency.lower() not in _RECURRING:
            return None
        return replace(self, completed=False, days_of_week=list(self.days_of_week))


@dataclass
class Pet:
    """An animal being cared for, owning a list of care tasks.

    Attributes:
        name: The pet's name.
        species: e.g. "dog", "cat", "other".
        age: The pet's age in years (optional).
        tasks: The care tasks belonging to this pet.
    """

    name: str
    species: str
    age: int | None = None
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a care task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet (no error if it isn't present)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def get_tasks(self) -> list[Task]:
        """Return this pet's care tasks."""
        return self.tasks


@dataclass
class Owner:
    """The pet owner, with a time budget, preferences, and pets.

    Attributes:
        name: The owner's name.
        available_minutes: Total time the owner has for care today.
        preferences: Free-form preferences, e.g. {"no_walks_after": "20:00"}.
        pets: The pets this owner cares for.
    """

    name: str
    available_minutes: int
    preferences: dict = field(default_factory=dict)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet with this owner."""
        self.pets.append(pet)

    def set_preference(self, key: str, value) -> None:
        """Set a single owner preference."""
        self.preferences[key] = value

    def all_tasks(self) -> list[Task]:
        """Flatten every task across all of this owner's pets into one list."""
        tasks: list[Task] = []
        for pet in self.pets:
            tasks.extend(pet.get_tasks())
        return tasks

    def filter_tasks(
        self,
        *,
        pet: Pet | str | None = None,
        completed: bool | None = None,
        category: str | None = None,
    ) -> list[Task]:
        """Return this owner's tasks narrowed by any combination of filters.

        Args:
            pet: Limit to a single pet, given as a Pet or its name. None keeps
                every pet's tasks.
            completed: Keep only tasks whose ``completed`` matches this. None
                keeps both done and pending tasks.
            category: Keep only tasks in this category. None keeps all.

        All arguments are keyword-only so calls read as
        ``owner.filter_tasks(pet="Mochi", completed=False)``.
        """
        if pet is None:
            tasks = self.all_tasks()
        else:
            name = pet.name if isinstance(pet, Pet) else pet
            tasks = [t for p in self.pets if p.name == name for t in p.get_tasks()]
        if completed is not None:
            tasks = [t for t in tasks if t.completed is completed]
        if category is not None:
            tasks = [t for t in tasks if t.category == category]
        return tasks


@dataclass
class ScheduledItem:
    """One placed task in a plan: a task and the clock window it occupies.

    Attributes:
        task: The task that was scheduled.
        start_time: When it starts, e.g. "08:00".
        end_time: When it ends, e.g. "08:20".
    """

    task: Task
    start_time: str
    end_time: str


@dataclass
class Conflict:
    """Two scheduled items whose clock windows overlap.

    Attributes:
        first: The earlier-listed overlapping item (schedule order).
        second: The later-listed overlapping item.
        first_pet: The pet ``first``'s task belongs to (None if unknown).
        second_pet: The pet ``second``'s task belongs to (None if unknown).
    """

    first: ScheduledItem
    second: ScheduledItem
    first_pet: Pet | None
    second_pet: Pet | None

    @property
    def same_pet(self) -> bool:
        """True when both tasks belong to the same (known) pet."""
        return self.first_pet is not None and self.first_pet is self.second_pet

    @property
    def scope(self) -> str:
        """Short label for who the clash is between, e.g. "Mochi vs Biscuit".

        Single source of truth for the same-pet vs cross-pet wording, shared
        by :meth:`Scheduler.explain` and :meth:`Scheduler.check_conflicts`.
        """
        if self.same_pet:
            return f"{self.first_pet.name} double-booked"
        first = self.first_pet.name if self.first_pet else "?"
        second = self.second_pet.name if self.second_pet else "?"
        return f"{first} vs {second}"


@dataclass
class Scheduler:
    """Builds a timed daily plan from an owner's tasks and constraints.

    Reads its candidate tasks, time budget, and preferences from the Owner,
    so there is a single source of truth for those constraints.

    Attributes:
        owner: The owner whose tasks and constraints drive the plan.
        day: The day being planned, e.g. "Mon" (matched against weekly tasks).
        start_time: Clock time the plan begins, e.g. "08:00".
        scheduled_items: ScheduledItems from the last generate_plan() call.
        dropped: Tasks left out of the last plan because time ran out.
    """

    owner: Owner
    day: str = "Mon"
    start_time: str = "08:00"
    scheduled_items: list[ScheduledItem] = field(default_factory=list)
    dropped: list[Task] = field(default_factory=list)

    def generate_plan(self) -> list[ScheduledItem]:
        """Filter, sort, budget, and time the day's tasks into a plan.

        Priority order decides *what* gets kept within the time budget; clock
        order decides *where* kept tasks land, so pinned ``preferred_time``
        tasks sit at their hour and the rest fill the gaps.
        """
        active = self._active_tasks(self.owner.all_tasks())
        ordered = self._sort_tasks(active)
        kept = self._fit_to_budget(ordered)
        # Anything ordered but not kept ran out of time. Compare by identity
        # (tasks can be equal by value), using a set of ids for an O(n) check.
        kept_ids = {id(k) for k in kept}
        self.dropped = [t for t in ordered if id(t) not in kept_ids]
        self.scheduled_items = self._assign_times(self.sort_by_time(kept))
        return self.scheduled_items

    def _active_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks due on ``self.day`` that are not yet completed."""
        return [t for t in tasks if t.is_due(self.day) and not t.completed]

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return the given tasks ordered by priority (then duration)."""
        return sorted(tasks, key=Task.sort_key)

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return the given tasks in clock order, pinned times first.

        Sorts on :meth:`Task.time_key`, so tasks with a ``preferred_time`` come
        first in ascending clock order and untimed (flexible) tasks fall to the
        back. Python's ``sorted`` is stable, so flexible tasks keep their
        incoming relative order rather than being shuffled — which lets the
        caller decide that order (e.g. by priority) before calling this.
        """
        return sorted(tasks, key=Task.time_key)

    def _fit_to_budget(self, tasks: list[Task]) -> list[Task]:
        """Keep leading tasks until one would exceed the time budget.

        Tradeoff: this is a greedy cut, not an optimal fit. It stops at the
        first task that doesn't fit and drops that task *and everything after
        it*, even if a later, shorter task would have fit the leftover minutes
        (e.g. a 90-min budget over durations [60, 40, 20] keeps only the 60 and
        wastes 30 minutes). We accept the wasted time on purpose: walking the
        already-priority-sorted list once preserves a strict "highest priority
        first" guarantee, runs in O(n), and is easy to explain to the owner.
        A knapsack-style packer would use the budget more fully but could keep
        a low-priority task over a high-priority one and is harder to reason
        about — not worth it for a single day's short task list.
        """
        budget = self.owner.available_minutes
        kept: list[Task] = []
        used = 0
        for task in tasks:
            if used + task.duration_minutes > budget:
                break
            kept.append(task)
            used += task.duration_minutes
        return kept

    def _assign_times(self, tasks: list[Task]) -> list[ScheduledItem]:
        """Assign a clock window to each kept task.

        A task with a ``preferred_time`` is pinned to that clock time; every
        other task stacks after the latest window used so far. Pinning can
        overlap a flexible task — :meth:`detect_conflicts` reports that.
        """
        items: list[ScheduledItem] = []
        cursor = _to_minutes(self.start_time)
        for task in tasks:
            if task.preferred_time:
                start = _to_minutes(task.preferred_time)
            else:
                start = cursor
            end = start + task.duration_minutes
            items.append(
                ScheduledItem(task, _to_clock(start), _to_clock(end))
            )
            # Advance the cursor past the latest end so far, so a pinned task
            # that runs long still pushes subsequent flexible tasks after it.
            cursor = max(cursor, end)
        return items

    def complete_task(self, task: Task) -> Task | None:
        """Mark ``task`` done and auto-queue its next occurrence.

        Flips the task's status to completed, then — if it recurs — builds a
        fresh pending instance (via :meth:`Task.next_occurrence`) and adds it
        to the same pet, so the task reappears on its next due day. Returns the
        newly queued Task, or None if the task doesn't recur.

        The task must belong to one of this owner's pets; if it isn't found,
        the task is still marked done but nothing is queued (returns None).
        """
        task.mark_done()
        upcoming = task.next_occurrence()
        if upcoming is None:
            return None
        pet = self._owning_pet(task)
        if pet is None:
            return None
        pet.add_task(upcoming)
        return upcoming

    def _owning_pet(self, task: Task) -> Pet | None:
        """Return the pet whose task list holds ``task``, or None if none does.

        Matches by object identity (``is``), not equality: two tasks can be
        equal by value (they're dataclasses), so ``in`` / ``==`` could point at
        the wrong pet when two pets share an identical-looking task. Scans pets
        in registration order and returns the first owner found.
        """
        for pet in self.owner.pets:
            if any(t is task for t in pet.get_tasks()):
                return pet
        return None

    def detect_conflicts(self) -> list[Conflict]:
        """Return every pair of scheduled items whose clock windows overlap.

        Two items conflict when one starts before the other ends. Compares
        every pair (fine for a day's worth of tasks) and returns each
        overlapping pair once, in schedule order. Each :class:`Conflict`
        records the owning pet of both tasks, so callers can tell a same-pet
        double-booking apart from a clash across two different pets (see
        :attr:`Conflict.same_pet`).
        """
        conflicts: list[Conflict] = []
        items = self.scheduled_items
        for i in range(len(items)):
            a = items[i]
            a_start, a_end = _to_minutes(a.start_time), _to_minutes(a.end_time)
            for j in range(i + 1, len(items)):
                b = items[j]
                b_start, b_end = _to_minutes(b.start_time), _to_minutes(b.end_time)
                if a_start < b_end and b_start < a_end:
                    conflicts.append(
                        Conflict(
                            a,
                            b,
                            self._owning_pet(a.task),
                            self._owning_pet(b.task),
                        )
                    )
        return conflicts

    def check_conflicts(self) -> str:
        """Lightweight conflict check that returns a warning string, not data.

        A forgiving companion to :meth:`detect_conflicts`. Instead of returning
        structured :class:`Conflict` objects (or letting a malformed clock time
        raise), it returns a short human-readable warning summarizing any
        overlaps, or an empty string when the plan is clean. It never raises —
        if anything goes wrong while checking, it reports that as a warning too
        — so a UI or script can print the result directly without a try/except.
        """
        try:
            conflicts = self.detect_conflicts()
        except Exception as exc:  # noqa: BLE001 - stay non-crashing by design
            return f"WARNING: could not check for conflicts: {exc}"
        if not conflicts:
            return ""
        parts = []
        for c in conflicts:
            parts.append(
                f"{c.first.task.description} ({c.first.start_time}) overlaps "
                f"{c.second.task.description} ({c.second.start_time}) "
                f"[{c.scope}]"
            )
        noun = "conflict" if len(conflicts) == 1 else "conflicts"
        return f"WARNING: {len(conflicts)} scheduling {noun}: " + "; ".join(parts)

    def explain(self) -> str:
        """Return a human-readable summary of scheduled and dropped tasks."""
        lines = [f"Plan for {self.owner.name} ({self.day}):"]
        if self.scheduled_items:
            for item in self.scheduled_items:
                t = item.task
                lines.append(
                    f"  {item.start_time}–{item.end_time}  {t.description} "
                    f"({t.duration_minutes} min) [priority: {t.priority}]"
                )
        else:
            lines.append("  (nothing scheduled)")
        if self.dropped:
            lines.append("Skipped (ran out of time):")
            for t in self.dropped:
                lines.append(
                    f"  - {t.description} "
                    f"({t.duration_minutes} min) [priority: {t.priority}]"
                )
        conflicts = self.detect_conflicts()
        if conflicts:
            lines.append("Conflicts (overlapping times):")
            for c in conflicts:
                a, b = c.first, c.second
                lines.append(
                    f"  - [{c.scope}] {a.task.description} "
                    f"({a.start_time}–{a.end_time}) overlaps "
                    f"{b.task.description} ({b.start_time}–{b.end_time})"
                )
        return "\n".join(lines)

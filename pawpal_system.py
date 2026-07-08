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

from dataclasses import dataclass, field

# Lower rank sorts first, so "high" comes before "low". Unknown priorities
# fall to the back rather than sorting alphabetically (the string-sort trap).
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


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
    """

    description: str
    duration_minutes: int
    priority: str = "medium"
    frequency: str = "daily"
    days_of_week: list[str] = field(default_factory=list)
    completed: bool = False
    category: str = "other"

    def sort_key(self) -> tuple:
        """Sort key ranking by priority first, then shorter duration."""
        return (_priority_rank(self.priority), self.duration_minutes)

    def is_due(self, day: str) -> bool:
        """Return True if this task should happen on the given day."""
        if self.frequency == "daily":
            return True
        if self.frequency == "weekly":
            wanted = {d.lower() for d in self.days_of_week}
            return day.lower() in wanted
        return False

    def mark_done(self) -> None:
        """Mark this task as completed."""
        self.completed = True


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
        """Filter, sort, budget, and time the day's tasks into a plan."""
        active = self._active_tasks(self.owner.all_tasks())
        ordered = self._sort_tasks(active)
        kept = self._fit_to_budget(ordered)
        # Anything ordered but not kept ran out of time (identity, not value).
        self.dropped = [t for t in ordered if not any(t is k for k in kept)]
        self.scheduled_items = self._assign_times(kept)
        return self.scheduled_items

    def _active_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return tasks due on ``self.day`` that are not yet completed."""
        return [t for t in tasks if t.is_due(self.day) and not t.completed]

    def _sort_tasks(self, tasks: list[Task]) -> list[Task]:
        """Return the given tasks ordered by priority (then duration)."""
        return sorted(tasks, key=Task.sort_key)

    def _fit_to_budget(self, tasks: list[Task]) -> list[Task]:
        """Keep leading tasks until one would exceed the time budget."""
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
        """Assign a clock window to each kept task, stacking back to back."""
        items: list[ScheduledItem] = []
        cursor = _to_minutes(self.start_time)
        for task in tasks:
            start = cursor
            end = cursor + task.duration_minutes
            items.append(
                ScheduledItem(task, _to_clock(start), _to_clock(end))
            )
            cursor = end
        return items

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
        return "\n".join(lines)

"""PawPal+ logic layer.

All backend domain classes live here: Task, Pet, Owner, and Scheduler.
This is the "skeleton" only — attributes are defined, but method bodies are
stubs to be implemented incrementally. Data-holder objects use dataclasses.

Design decisions (from the UML brainstorm):
  * The plan assigns clock times, starting at Scheduler.start_time.
  * When tasks exceed the time budget, keep highest-priority tasks and drop
    the lowest-priority overflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Task:
    """One care task (a walk, a feeding, meds, etc.).

    Attributes:
        title: Human-readable name, e.g. "Morning walk".
        duration_minutes: How long the task takes, in minutes.
        priority: One of "low", "medium", "high".
        category: Kind of task, e.g. "walk", "feeding", "meds", "grooming".
    """

    title: str
    duration_minutes: int
    priority: str = "medium"
    category: str = "other"

    def sort_key(self) -> tuple:
        """Return a sort key ordering tasks by priority, then duration."""
        raise NotImplementedError


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
        raise NotImplementedError

    def remove_task(self, task: Task) -> None:
        """Remove a care task from this pet."""
        raise NotImplementedError

    def get_tasks(self) -> list[Task]:
        """Return this pet's care tasks."""
        raise NotImplementedError


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
        raise NotImplementedError

    def set_preference(self, key: str, value) -> None:
        """Set a single owner preference."""
        raise NotImplementedError


@dataclass
class Scheduler:
    """Builds a timed daily plan from tasks and the owner's constraints.

    Attributes:
        tasks: Candidate tasks to consider.
        available_minutes: Time budget for the day.
        start_time: Clock time the plan begins, e.g. "08:00".
        scheduled_items: Result of the last plan; each item pairs a task
            with its assigned start time.
    """

    tasks: list[Task]
    available_minutes: int
    start_time: str = "08:00"
    scheduled_items: list = field(default_factory=list)

    def generate_plan(self) -> list:
        """Build and return the daily plan.

        Flow: sort by priority -> fit to the time budget (dropping
        lowest-priority overflow) -> assign clock times from start_time.
        Stores the result in scheduled_items and returns it.
        """
        raise NotImplementedError

    def _sort_tasks(self) -> list[Task]:
        """Return tasks ordered by priority (then duration)."""
        raise NotImplementedError

    def _fit_to_budget(self) -> list[Task]:
        """Return the tasks that fit within available_minutes."""
        raise NotImplementedError

    def _assign_times(self) -> list:
        """Assign a clock time to each kept task, stacking durations."""
        raise NotImplementedError

    def explain(self) -> str:
        """Return a human-readable explanation of the plan.

        Covers chosen tasks (why/when) and any dropped tasks.
        """
        raise NotImplementedError

"""Temporary demo / testing ground for the PawPal+ logic layer.

Run in the terminal to verify the domain classes and scheduler work:

    python main.py
"""

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_owner() -> Owner:
    """Create a sample owner with two pets and a handful of tasks.

    Tasks are deliberately added *out of clock order* (e.g. the 08:05 vet call
    before the 08:00 meds) so the sorting demo below has something real to fix.
    One task is pre-marked completed to exercise the status filter.
    """
    owner = Owner("Jordan", available_minutes=90)

    # --- Pet 1: a dog ---
    biscuit = Pet("Biscuit", "dog", age=4)
    # Pinned to 08:00 and added FIRST, even though the 08:00 Meds task exists
    # below — out of clock order, and at the *same time* as Meds so the
    # scheduler has a genuine conflict to warn about.
    biscuit.add_task(
        Task("Vet call", 20, priority="high", category="meds", preferred_time="08:00")
    )
    biscuit.add_task(Task("Morning walk", 30, priority="high", category="walk"))
    biscuit.add_task(Task("Training", 20, priority="medium", category="enrichment"))
    # Already done today — should be filtered out by completed=False.
    already_fed = Task("Feeding", 10, priority="high", category="feeding")
    already_fed.mark_done()
    biscuit.add_task(already_fed)

    # --- Pet 2: a cat ---
    mochi = Pet("Mochi", "cat", age=2)
    mochi.add_task(Task("Clean litter", 10, priority="medium", category="grooming"))
    mochi.add_task(Task("Feeding", 5, priority="high", category="feeding"))
    # Pinned to 08:00 but added AFTER the 08:05 vet call above — again out of
    # order, and overlapping the vet call so conflict detection has a target.
    mochi.add_task(
        Task("Meds", 10, priority="high", category="meds", preferred_time="08:00")
    )
    mochi.add_task(
        Task(
            "Weekly brush",
            15,
            priority="low",
            frequency="weekly",
            days_of_week=["Sun"],
            category="grooming",
        )
    )

    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    return owner


def demo_sorting(scheduler: Scheduler, owner: Owner) -> None:
    """Show that sort_by_time() reorders out-of-order tasks into clock order."""
    print("\nSorting demo — tasks as added (insertion order)")
    print("-" * 48)
    for t in owner.all_tasks():
        pinned = t.preferred_time or "—"
        print(f"  [{pinned}] {t.description}")

    print("\nSame tasks after Scheduler.sort_by_time()")
    print("-" * 48)
    for t in scheduler.sort_by_time(owner.all_tasks()):
        pinned = t.preferred_time or "(flexible)"
        print(f"  [{pinned}] {t.description}")


def demo_filtering(owner: Owner) -> None:
    """Show filter_tasks() narrowing by completion status and by pet name."""
    print("\nFiltering demo — Owner.filter_tasks()")
    print("-" * 48)

    pending = owner.filter_tasks(completed=False)
    print(f"Pending (completed=False): {[t.description for t in pending]}")

    done = owner.filter_tasks(completed=True)
    print(f"Done (completed=True):     {[t.description for t in done]}")

    mochi_tasks = owner.filter_tasks(pet="Mochi")
    print(f"Mochi's tasks (pet='Mochi'): {[t.description for t in mochi_tasks]}")

    mochi_pending = owner.filter_tasks(pet="Mochi", completed=False)
    print(f"Mochi + pending (combined):  {[t.description for t in mochi_pending]}")


def main() -> None:
    owner = build_demo_owner()

    print("=" * 48)
    print(f"PawPal+ demo — owner: {owner.name}")
    print(f"Pets: {', '.join(p.name for p in owner.pets)}")
    print(f"Time available today: {owner.available_minutes} min")
    print("=" * 48)

    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()

    demo_sorting(scheduler, owner)
    demo_filtering(owner)

    print("\nToday's Schedule")
    print("-" * 48)
    print(scheduler.explain())

    # Lightweight conflict check: prints a warning if any tasks overlap,
    # otherwise reports that the plan is clean. Never raises.
    print("\nConflict warning")
    print("-" * 48)
    warning = scheduler.check_conflicts()
    print(warning if warning else "OK: no conflicts detected.")


if __name__ == "__main__":
    main()

"""Temporary demo / testing ground for the PawPal+ logic layer.

Run in the terminal to verify the domain classes and scheduler work:

    python main.py
"""

from pawpal_system import Owner, Pet, Scheduler, Task


def build_demo_owner() -> Owner:
    """Create a sample owner with two pets and a handful of tasks."""
    owner = Owner("Jordan", available_minutes=90)

    # --- Pet 1: a dog ---
    biscuit = Pet("Biscuit", "dog", age=4)
    biscuit.add_task(Task("Morning walk", 30, priority="high", category="walk"))
    biscuit.add_task(Task("Feeding", 10, priority="high", category="feeding"))
    biscuit.add_task(Task("Training", 20, priority="medium", category="enrichment"))

    # --- Pet 2: a cat ---
    mochi = Pet("Mochi", "cat", age=2)
    mochi.add_task(Task("Feeding", 5, priority="high", category="feeding"))
    mochi.add_task(Task("Clean litter", 10, priority="medium", category="grooming"))
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


def main() -> None:
    owner = build_demo_owner()

    print("=" * 48)
    print(f"PawPal+ demo — owner: {owner.name}")
    print(f"Pets: {', '.join(p.name for p in owner.pets)}")
    print(f"Time available today: {owner.available_minutes} min")
    print("=" * 48)

    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()

    print("\nToday's Schedule")
    print("-" * 48)
    print(scheduler.explain())


if __name__ == "__main__":
    main()

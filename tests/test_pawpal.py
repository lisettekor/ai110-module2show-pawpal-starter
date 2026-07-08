"""Basic tests for the PawPal+ logic layer."""

from pawpal_system import Owner, Pet, ScheduledItem, Scheduler, Task


def test_task_completion_changes_status():
    """Calling mark_done() flips the task's completed status to True."""
    task = Task("Morning walk", 20)
    assert task.completed is False
    task.mark_done()
    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet increases that pet's task count."""
    pet = Pet("Biscuit", "dog")
    assert len(pet.get_tasks()) == 0
    pet.add_task(Task("Feeding", 10))
    assert len(pet.get_tasks()) == 1


# --- Recurring tasks --------------------------------------------------------


def test_daily_task_due_every_day():
    task = Task("Feeding", 10, frequency="daily")
    assert all(task.is_due(d) for d in ["Mon", "Sat", "Sun"])


def test_weekly_task_due_only_on_listed_days():
    task = Task("Brush", 15, frequency="weekly", days_of_week=["Sun"])
    assert task.is_due("Sun") is True
    assert task.is_due("Mon") is False


def test_weekdays_and_weekends_recurrence():
    weekday_task = Task("Work walk", 20, frequency="weekdays")
    weekend_task = Task("Long hike", 60, frequency="weekends")
    assert weekday_task.is_due("Wed") is True
    assert weekday_task.is_due("Sat") is False
    assert weekend_task.is_due("Sat") is True
    assert weekend_task.is_due("Wed") is False


def test_unknown_frequency_is_never_due():
    task = Task("Odd", 5, frequency="monthly")
    assert task.is_due("Mon") is False


# --- Filtering by pet / status ----------------------------------------------


def _owner_with_two_pets() -> Owner:
    owner = Owner("Jordan", available_minutes=120)
    dog = Pet("Biscuit", "dog")
    dog.add_task(Task("Walk", 30, category="walk"))
    dog.add_task(Task("Feeding", 10, category="feeding", completed=True))
    cat = Pet("Mochi", "cat")
    cat.add_task(Task("Litter", 10, category="grooming"))
    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner


def test_filter_by_pet_name():
    owner = _owner_with_two_pets()
    tasks = owner.filter_tasks(pet="Mochi")
    assert [t.description for t in tasks] == ["Litter"]


def test_filter_by_completion_status():
    owner = _owner_with_two_pets()
    assert len(owner.filter_tasks(completed=False)) == 2
    assert len(owner.filter_tasks(completed=True)) == 1


def test_filter_combines_pet_and_category():
    owner = _owner_with_two_pets()
    tasks = owner.filter_tasks(pet="Biscuit", category="walk")
    assert [t.description for t in tasks] == ["Walk"]


# --- Sorting by time --------------------------------------------------------


def test_sort_by_time_orders_pinned_first_then_untimed():
    owner = Owner("Jordan", available_minutes=120)
    scheduler = Scheduler(owner)
    late = Task("Meds", 5, preferred_time="14:00")
    early = Task("Walk", 20, preferred_time="07:30")
    flexible = Task("Play", 15)
    ordered = scheduler.sort_by_time([flexible, late, early])
    assert [t.description for t in ordered] == ["Walk", "Meds", "Play"]


def test_generated_plan_items_are_in_chronological_order():
    """Sorting correctness: the finished plan's items run in clock order.

    Tasks are added out of order (a late pinned task first), but every
    ScheduledItem's start_time must be >= the one before it.
    """
    owner = Owner("Jordan", available_minutes=240)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Evening meds", 10, preferred_time="18:00"))
    pet.add_task(Task("Morning walk", 30, preferred_time="07:00"))
    pet.add_task(Task("Midday play", 15, preferred_time="12:00"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="07:00")

    items = scheduler.generate_plan()
    starts = [item.start_time for item in items]
    assert starts == sorted(starts)
    assert [i.task.description for i in items] == [
        "Morning walk",
        "Midday play",
        "Evening meds",
    ]


# --- Conflict detection -----------------------------------------------------


def test_two_pinned_tasks_overlapping_is_a_conflict():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    # Both tasks are pinned to fixed times whose windows overlap:
    # meds 08:00–08:20 and a vet call 08:10–08:40.
    pet.add_task(Task("Meds", 20, priority="high", preferred_time="08:00"))
    pet.add_task(Task("Vet call", 30, priority="high", preferred_time="08:10"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()
    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1


def test_two_tasks_at_the_exact_same_time_conflict():
    """Conflict detection: identical start times are flagged as a clash.

    Two tasks pinned to the very same clock time (a true duplicate booking)
    produce exactly one conflict whose windows share a start_time.
    """
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Meds", 15, priority="high", preferred_time="08:00"))
    pet.add_task(Task("Feeding", 10, priority="high", preferred_time="08:00"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()

    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1
    assert conflicts[0].first.start_time == conflicts[0].second.start_time == "08:00"


def test_same_pet_conflict_is_flagged_as_same_pet():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Meds", 20, priority="high", preferred_time="08:00"))
    pet.add_task(Task("Vet call", 30, priority="high", preferred_time="08:10"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()
    conflict = scheduler.detect_conflicts()[0]
    assert conflict.same_pet is True
    assert conflict.first_pet is pet and conflict.second_pet is pet


def test_conflict_across_two_different_pets_is_detected():
    owner = Owner("Jordan", available_minutes=120)
    biscuit = Pet("Biscuit", "dog")
    mochi = Pet("Mochi", "cat")
    # One pinned task per pet, overlapping windows: the owner can't be in two
    # places at once, so this is a cross-pet clash.
    biscuit.add_task(Task("Walk", 30, priority="high", preferred_time="08:00"))
    mochi.add_task(Task("Meds", 10, priority="high", preferred_time="08:15"))
    owner.add_pet(biscuit)
    owner.add_pet(mochi)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()

    conflicts = scheduler.detect_conflicts()
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.same_pet is False
    involved = (conflict.first_pet, conflict.second_pet)
    assert biscuit in involved and mochi in involved


def test_back_to_back_tasks_do_not_conflict():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Walk", 30))
    pet.add_task(Task("Feeding", 10))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()
    assert scheduler.detect_conflicts() == []


# --- Lightweight conflict warning (check_conflicts) -------------------------


def test_check_conflicts_returns_empty_string_when_clean():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Walk", 30))
    owner.add_pet(pet)
    scheduler = Scheduler(owner)
    scheduler.generate_plan()
    assert scheduler.check_conflicts() == ""


def test_check_conflicts_returns_warning_message_on_overlap():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    pet.add_task(Task("Meds", 20, priority="high", preferred_time="08:00"))
    pet.add_task(Task("Vet call", 30, priority="high", preferred_time="08:10"))
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon", start_time="08:00")
    scheduler.generate_plan()
    warning = scheduler.check_conflicts()
    assert warning.startswith("WARNING")
    assert "conflict" in warning
    assert "Meds" in warning and "Vet call" in warning


def test_check_conflicts_warns_instead_of_crashing_on_bad_time():
    # A malformed clock time would make detect_conflicts raise; the lightweight
    # check must swallow that and return a warning string instead.
    owner = Owner("Jordan", available_minutes=120)
    owner.add_pet(Pet("Biscuit", "dog"))
    scheduler = Scheduler(owner)
    scheduler.scheduled_items = [
        ScheduledItem(Task("Meds", 5), "not-a-time", "worse"),
        ScheduledItem(Task("Walk", 5), "08:00", "08:05"),
    ]
    warning = scheduler.check_conflicts()  # must not raise
    assert warning.startswith("WARNING")
    assert "could not check" in warning


# --- Recurrence regeneration on completion ----------------------------------


def test_next_occurrence_of_daily_task_is_a_fresh_pending_copy():
    task = Task("Feeding", 10, frequency="daily")
    task.mark_done()
    nxt = task.next_occurrence()
    assert nxt is not None
    assert nxt is not task
    assert nxt.completed is False
    assert nxt.description == "Feeding"


def test_next_occurrence_of_weekly_task_copies_days_independently():
    task = Task("Brush", 15, frequency="weekly", days_of_week=["Sun"])
    nxt = task.next_occurrence()
    assert nxt.days_of_week == ["Sun"]
    # Mutating the copy must not touch the original's list.
    nxt.days_of_week.append("Wed")
    assert task.days_of_week == ["Sun"]


def test_non_recurring_task_has_no_next_occurrence():
    task = Task("One-off vet visit", 30, frequency="monthly")
    assert task.next_occurrence() is None


def test_completing_daily_task_queues_a_new_pending_instance():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    feeding = Task("Feeding", 10, frequency="daily")
    pet.add_task(feeding)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    assert len(pet.get_tasks()) == 1
    queued = scheduler.complete_task(feeding)

    # Original is done; a fresh pending copy was added to the same pet.
    assert feeding.completed is True
    assert queued is not None and queued.completed is False
    assert len(pet.get_tasks()) == 2
    assert owner.filter_tasks(completed=False) == [queued]


def test_completing_daily_task_creates_one_due_the_following_day():
    """Recurrence logic: completing a daily task queues one for the next day.

    Plan Monday, complete the daily task, then confirm the freshly queued
    instance is pending and due Tuesday (the following day).
    """
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    feeding = Task("Feeding", 10, frequency="daily")
    pet.add_task(feeding)
    owner.add_pet(pet)
    scheduler = Scheduler(owner, day="Mon")

    queued = scheduler.complete_task(feeding)

    assert feeding.completed is True
    assert queued is not None
    assert queued.completed is False
    # "The following day": a daily task is due Tuesday (and every day).
    assert queued.is_due("Tue") is True
    # And it's the only pending task left for tomorrow's plan.
    tomorrow = Scheduler(owner, day="Tue")
    planned = tomorrow.generate_plan()
    assert [i.task for i in planned] == [queued]


def test_completing_non_recurring_task_queues_nothing():
    owner = Owner("Jordan", available_minutes=120)
    pet = Pet("Biscuit", "dog")
    one_off = Task("Nail trim", 15, frequency="monthly")
    pet.add_task(one_off)
    owner.add_pet(pet)
    scheduler = Scheduler(owner)

    assert scheduler.complete_task(one_off) is None
    assert one_off.completed is True
    assert len(pet.get_tasks()) == 1

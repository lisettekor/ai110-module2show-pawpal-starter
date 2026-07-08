"""Basic tests for the PawPal+ logic layer."""

from pawpal_system import Pet, Task


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

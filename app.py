import streamlit as st

from pawpal_system import Owner, Pet, Scheduler, Task

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_owner(name: str, available_minutes: int) -> Owner:
    """Return the Owner from the session vault, creating it once if absent.

    Streamlit reruns the whole script on every interaction, so any object
    built inside a run is thrown away at the end of that run. Storing the
    Owner in st.session_state lets the *same* instance (with its pets and
    tasks) persist across reruns instead of being rebuilt every time. We
    reuse it and just sync the editable fields.
    """
    if "owner" not in st.session_state:
        st.session_state.owner = Owner(name, available_minutes=available_minutes)
    owner = st.session_state.owner
    owner.name = name
    owner.available_minutes = available_minutes
    return owner


st.title("🐾 PawPal+")

st.markdown(
    """
PawPal+ helps a pet owner plan care tasks for the day based on constraints
like available time, priority, and how often a task recurs.

Add your owner, pets, and tasks below, then generate a schedule.
"""
)

with st.expander("How it works", expanded=False):
    st.markdown(
        """
This UI is a thin layer over the logic in `pawpal_system.py`:

- **Owner** holds the day's time budget and preferences.
- **Pet** holds its own care **Tasks**.
- **Scheduler** filters tasks to those due today (and not completed),
  sorts them by priority, drops the lowest-priority tasks that don't fit
  the time budget, assigns clock times, and flags any overlapping tasks
  as conflicts.
"""
    )

st.divider()

# --- Owner + day constraints ------------------------------------------------
st.subheader("Owner & day")
owner_name = st.text_input("Owner name", value="Jordan")

col_a, col_b, col_c = st.columns(3)
with col_a:
    available_minutes = st.number_input(
        "Time available (min)", min_value=15, max_value=600, value=90, step=15
    )
with col_b:
    day = st.selectbox("Day", DAYS, index=0)
with col_c:
    start_time = st.text_input("Start time (HH:MM)", value="08:00")

# The persisted Owner is our single source of truth from here on.
owner = get_owner(owner_name, int(available_minutes))

st.divider()

# --- Add a pet --------------------------------------------------------------
st.subheader("Pets")
col_p1, col_p2, col_p3 = st.columns([2, 2, 1])
with col_p1:
    new_pet_name = st.text_input("Pet name", value="Mochi")
with col_p2:
    new_pet_species = st.selectbox("Species", ["dog", "cat", "other"])
with col_p3:
    new_pet_age = st.number_input("Age", min_value=0, max_value=40, value=2)

if st.button("Add pet"):
    if not new_pet_name.strip():
        st.warning("Give the pet a name first.")
    else:
        # -> calls Owner.add_pet() from the logic layer
        owner.add_pet(Pet(new_pet_name.strip(), new_pet_species, age=int(new_pet_age)))
        st.success(f"Added {new_pet_name.strip()} to {owner.name}'s pets.")

if not owner.pets:
    st.info("No pets yet. Add one above to start scheduling tasks.")

st.divider()

# --- Add a task to a pet ----------------------------------------------------
st.subheader("Tasks")

if owner.pets:
    # Choose which pet the task belongs to (by index, so duplicate names are ok).
    pet_index = st.selectbox(
        "Pet",
        options=list(range(len(owner.pets))),
        format_func=lambda i: f"{owner.pets[i].name} ({owner.pets[i].species})",
    )
    selected_pet = owner.pets[pet_index]

    col1, col2, col3 = st.columns(3)
    with col1:
        description = st.text_input("Task", value="Morning walk")
    with col2:
        duration = st.number_input(
            "Duration (min)", min_value=1, max_value=240, value=20
        )
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    col4, col5 = st.columns(2)
    with col4:
        frequency = st.selectbox("Frequency", ["daily", "weekly"])
    with col5:
        days_of_week = st.multiselect(
            "Days (weekly only)", DAYS, disabled=frequency == "daily"
        )

    if st.button("Add task"):
        if not description.strip():
            st.warning("Give the task a description first.")
        else:
            # -> calls Pet.add_task() from the logic layer
            selected_pet.add_task(
                Task(
                    description=description.strip(),
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=frequency,
                    days_of_week=list(days_of_week),
                )
            )
            st.success(f"Added '{description.strip()}' to {selected_pet.name}.")

    # Show each pet's current tasks (read via Pet.get_tasks()).
    for pet in owner.pets:
        tasks = pet.get_tasks()
        st.markdown(f"**{pet.name}** — {len(tasks)} task(s)")
        if tasks:
            st.table(
                [
                    {
                        "Task": t.description,
                        "Duration": f"{t.duration_minutes} min",
                        "Priority": t.priority,
                        "Frequency": t.frequency,
                        "Days": ", ".join(t.days_of_week) if t.days_of_week else "—",
                    }
                    for t in tasks
                ]
            )
else:
    st.caption("Add a pet before adding tasks.")

st.divider()

# --- Generate schedule ------------------------------------------------------
st.subheader("Build Schedule")

if st.button("Generate schedule", type="primary"):
    if not owner.all_tasks():
        st.warning("Add at least one task first.")
    else:
        # The Owner already holds all pets/tasks, so just schedule it.
        scheduler = Scheduler(owner, day=day, start_time=start_time)
        scheduler.generate_plan()

        st.markdown(f"### 🗓️ Today's Schedule ({day})")

        # At-a-glance summary of the sorted plan: how many tasks fit, how many
        # were skipped, and how the time budget was spent.
        used = sum(i.task.duration_minutes for i in scheduler.scheduled_items)
        if scheduler.scheduled_items:
            st.success(
                f"Planned {len(scheduler.scheduled_items)} task(s) for {day}, "
                f"using {used} of {owner.available_minutes} min."
            )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scheduled", len(scheduler.scheduled_items))
        m2.metric("Skipped", len(scheduler.dropped))
        m3.metric("Minutes used", used)
        m4.metric("Minutes free", max(0, owner.available_minutes - used))

        if scheduler.scheduled_items:
            st.table(
                [
                    {
                        "Start": item.start_time,
                        "End": item.end_time,
                        "Task": item.task.description,
                        "Duration": f"{item.task.duration_minutes} min",
                        "Priority": item.task.priority,
                    }
                    for item in scheduler.scheduled_items
                ]
            )
        else:
            st.info("Nothing could be scheduled for this day.")

        if scheduler.dropped:
            st.warning(f"Skipped {len(scheduler.dropped)} task(s) — ran out of time:")
            st.table(
                [
                    {
                        "Task": t.description,
                        "Duration": f"{t.duration_minutes} min",
                        "Priority": t.priority,
                    }
                    for t in scheduler.dropped
                ]
            )

        # Surface overlapping time windows using the Scheduler's own conflict
        # detection. detect_conflicts() gives structured Conflict objects (with
        # a human-readable `scope` label); check_conflicts() is the never-raises
        # string version we fall back on if anything goes wrong.
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.error(f"⚠️ {len(conflicts)} scheduling conflict(s) detected:")
            for c in conflicts:
                st.write(
                    f"- **[{c.scope}]** {c.first.task.description} "
                    f"({c.first.start_time}–{c.first.end_time}) overlaps "
                    f"{c.second.task.description} "
                    f"({c.second.start_time}–{c.second.end_time})"
                )
        else:
            warning = scheduler.check_conflicts()
            if warning:
                # Non-empty only if check_conflicts() hit a problem detect_
                # conflicts() couldn't (e.g. a malformed time); show it plainly.
                st.warning(warning)
            else:
                st.success("No scheduling conflicts.")

        with st.expander("Why this plan?"):
            st.code(scheduler.explain(), language="text")

# --- Reset ------------------------------------------------------------------
if st.button("Start over (clear owner & pets)"):
    st.session_state.pop("owner", None)
    st.rerun()

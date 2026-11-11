import copy
from typing import Dict, Any, List, Tuple
import pandas as pd
import streamlit as st

from services.exercise_links import exercise_demo_url
from services.planner import HealthForgePlanner, failed_safety_audit
from ui.alerts import show_error_alert


def render_header(app_name: str, tagline: str) -> None:
    st.title(app_name)
    st.caption(tagline)


AGE_RANGES = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["Prefer not to say", "Female", "Male", "Non-binary", "Other"]
EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]
GOALS = [
    "Build muscle",
    "Lose fat",
    "Improve general health",
    "Increase strength",
    "Improve endurance",
]
SESSION_LENGTHS = ["30-45 minutes", "45-60 minutes", "60-75 minutes", "75+ minutes"]
EQUIPMENT_OPTIONS = [
    "None (bodyweight only)",
    "Dumbbells",
    "Barbell",
    "Machines",
    "Resistance bands",
    "Kettlebells",
    "Cable stack",
]
DIET_PREFERENCES = [
    "No specific preference",
    "High-protein omnivore",
    "Vegetarian",
    "Vegan",
    "Pescatarian",
    "Halal",
    "Kosher",
]

# Form defaults, keyed by profile field. A loaded plan replaces these with its own
# profile (see set_profile_form_values).
PROFILE_FORM_DEFAULTS: Dict[str, Any] = {
    "name": "",
    "age_range": "25-34",
    "gender": "Prefer not to say",
    "experience_level": "Beginner",
    "primary_goal": "Build muscle",
    "secondary_goal": "None",
    "days_per_week": 4,
    "session_length": "45-60 minutes",
    "equipment": ["None (bodyweight only)"],
    "limitations": "",
    "diet_preference": "High-protein omnivore",
    "diet_restrictions": "",
    "schedule": "",
    "notes": "",
}

_SELECT_OPTIONS = {
    "age_range": AGE_RANGES,
    "gender": GENDERS,
    "experience_level": EXPERIENCE_LEVELS,
    "primary_goal": GOALS,
    "secondary_goal": ["None"] + GOALS,
    "session_length": SESSION_LENGTHS,
    "diet_preference": DIET_PREFERENCES,
}


def _form_key(field: str) -> str:
    # The version changes whenever a saved plan is loaded, so every field becomes a
    # brand-new widget that starts from the loaded value. This also discards anything
    # typed into the form but never submitted.
    return f"form_{field}_v{st.session_state.get('profile_form_version', 0)}"


def _form_values() -> Dict[str, Any]:
    return st.session_state.get("profile_form_values", PROFILE_FORM_DEFAULTS)


def set_profile_form_values(profile: Dict[str, Any]) -> None:
    """
    Prefills the profile form from a saved profile. Must run before the form
    renders. Values that no longer match the form's options fall back to defaults.
    """
    values = dict(PROFILE_FORM_DEFAULTS)
    for field in PROFILE_FORM_DEFAULTS:
        value = profile.get(field)
        if field == "secondary_goal" and not value:
            value = "None"

        if field in _SELECT_OPTIONS:
            if value not in _SELECT_OPTIONS[field]:
                continue
        elif field == "equipment":
            if not isinstance(value, list):
                continue
            value = [v for v in value if v in EQUIPMENT_OPTIONS]
        elif field == "days_per_week":
            if not isinstance(value, int) or not 2 <= value <= 7:
                continue
        elif not isinstance(value, str):
            continue

        values[field] = value

    # Values are passed to the widgets as their starting values rather than set through
    # st.session_state: Streamlit 1.40 can show text areas blank when their value is
    # changed through session state after the first load.
    st.session_state.profile_form_values = values
    st.session_state.profile_form_version = st.session_state.get("profile_form_version", 0) + 1


def render_user_profile_form() -> Dict[str, Any]:
    st.subheader("Your Profile")
    v = _form_values()

    def select(label: str, field: str) -> str:
        options = _SELECT_OPTIONS[field]
        return st.selectbox(label, options, index=options.index(v[field]), key=_form_key(field))

    with st.form("user_profile_form"):
        name = st.text_input("Name (optional)", value=v["name"], key=_form_key("name"))
        age_range = select("Age range", "age_range")
        gender = select("Gender (optional)", "gender")
        experience_level = select("Training experience", "experience_level")
        primary_goal = select("Primary goal", "primary_goal")
        secondary_goal = select("Secondary goal (optional)", "secondary_goal")
        days_per_week = st.slider(
            "Training days per week", 2, 7, value=v["days_per_week"], key=_form_key("days_per_week")
        )
        session_length = select("Typical session length", "session_length")
        equipment = st.multiselect(
            "Equipment available", EQUIPMENT_OPTIONS, default=v["equipment"], key=_form_key("equipment")
        )
        limitations = st.text_area(
            "Injuries / limitations (non-medical description)",
            value=v["limitations"],
            placeholder="E.g., mild knee discomfort with deep squats, avoid overhead pressing, etc.",
            key=_form_key("limitations"),
        )
        diet_preference = select("Dietary preference", "diet_preference")
        diet_restrictions = st.text_input(
            "Dietary restrictions",
            value=v["diet_restrictions"],
            placeholder="E.g., lactose intolerant, gluten-free, nut allergy (do NOT ask for medical treatment).",
            key=_form_key("diet_restrictions"),
        )
        schedule = st.text_area(
            "Typical weekly schedule / constraints",
            value=v["schedule"],
            placeholder="E.g., office job 9-5, can train mornings or evenings, weekends more flexible.",
            key=_form_key("schedule"),
        )
        notes = st.text_area(
            "Additional notes or preferences",
            value=v["notes"],
            placeholder="E.g., prefer dumbbells over barbells, like group classes, hate running, etc.",
            key=_form_key("notes"),
        )

        submitted = st.form_submit_button("Generate Plan")

        profile = {
            "name": name,
            "age_range": age_range,
            "gender": gender,
            "experience_level": experience_level,
            "primary_goal": primary_goal,
            "secondary_goal": secondary_goal if secondary_goal != "None" else "",
            "days_per_week": days_per_week,
            "session_length": session_length,
            "equipment": equipment,
            "limitations": limitations,
            "diet_preference": diet_preference,
            "diet_restrictions": diet_restrictions,
            "schedule": schedule,
            "notes": notes,
        }

        return profile, submitted


def render_plan(plan: Dict[str, Any]) -> None:
    summary = plan.get("summary", "")
    workout_plan = plan.get("workout_plan", {})
    nutrition_plan = plan.get("nutrition_plan", {})
    habits = plan.get("habits_and_lifestyle", {})
    disclaimers = plan.get("disclaimers", [])

    st.subheader("Overview")
    st.write(summary)

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Workout Plan", "Nutrition Plan", "Habits & Lifestyle", "Disclaimers"]
    )

    with tab1:
        _render_workout_tab(plan, workout_plan)

    with tab2:
        _render_nutrition_tab(nutrition_plan)

    with tab3:
        _render_habits_tab(habits)

    with tab4:
        _render_disclaimers_tab(disclaimers)


def _swap_key(day_index: int, exercise_index: int, exercise: Dict[str, Any]) -> str:
    # Includes the name so a swapped-in exercise starts unticked, and a version that
    # clear_swap_selection bumps to untick everything.
    version = st.session_state.get("swap_tick_version", 0)
    return f"swap_pick_{day_index}_{exercise_index}_{exercise.get('name', '')}_v{version}"


def clear_swap_selection() -> None:
    """Unticks every exercise and meal on the next run."""
    st.session_state.swap_tick_version = st.session_state.get("swap_tick_version", 0) + 1


def selected_swap_ids(plan: Dict[str, Any]) -> List[str]:
    """
    Exercises ticked for swapping in the Workout Plan tab, as "d<day>e<exercise>" ids.
    """
    selected = []
    for d, day in enumerate(plan.get("workout_plan", {}).get("weekly_split", [])):
        for e, ex in enumerate(day.get("exercises", [])):
            if isinstance(ex, dict) and st.session_state.get(_swap_key(d, e, ex)):
                selected.append(f"d{d}e{e}")
    return selected


def _meal_swap_key(meal_index: int, meal: Dict[str, Any]) -> str:
    # Includes the meal so a swapped-in one starts unticked (see also _swap_key).
    version = st.session_state.get("swap_tick_version", 0)
    return f"meal_swap_pick_{meal_index}_{meal.get('example', '')}_v{version}"


def selected_meal_swap_ids(plan: Dict[str, Any]) -> List[str]:
    """
    Meals ticked for swapping in the Nutrition tab, as "m<meal>" ids.
    """
    meals = plan.get("nutrition_plan", {}).get("daily_structure", [])
    return [
        f"m{m}" for m, meal in enumerate(meals)
        if isinstance(meal, dict) and st.session_state.get(_meal_swap_key(m, meal))
    ]


def _render_workout_tab(plan: Dict[str, Any], workout_plan: Dict[str, Any]) -> None:
    weekly_split = workout_plan.get("weekly_split", [])
    progression_notes = workout_plan.get("progression_notes", "")

    if not weekly_split:
        st.info("No workout plan available.")
        return

    _render_safety_check_prompt(plan)
    st.caption(
        "✏️ Use **Edit this day** to change exercises yourself, or ☑️ tick exercises and "
        "click **Find Replacements** below the plan to choose from suggestions."
    )

    for d, day in enumerate(weekly_split):
        if st.session_state.get("editing_day") == d:
            _render_day_editor(plan, d, day)
            continue

        st.markdown(f"### {day.get('day', 'Day')}")
        st.write(day.get("focus", ""))

        exercises = day.get("exercises", [])
        if exercises:
            for e, ex in enumerate(exercises):
                if not isinstance(ex, dict):
                    st.markdown(f"- {ex}")
                    continue
                name = ex.get('name', 'Exercise')
                st.checkbox(f"**{name}**", key=_swap_key(d, e, ex))
                st.write(
                    f"  Sets: {ex.get('sets', '')} | Reps: {ex.get('reps', '')}  \n"
                    f"  Notes: {ex.get('notes', '')}  \n"
                    f"  [▶️ Watch a demo]({exercise_demo_url(name)})"
                )

        if st.button("✏️ Edit this day", key=f"edit_day_{d}"):
            st.session_state.editing_day = d
            st.rerun()

    if progression_notes:
        st.markdown("#### Progression Notes")
        st.write(progression_notes)


_EDITOR_COLUMNS = ["Exercise", "Sets", "Reps", "Notes"]


def _render_day_editor(plan: Dict[str, Any], day_index: int, day: Dict[str, Any]) -> None:
    """
    Lets the user change one day's focus and exercises directly, with no AI involved.
    """
    st.markdown(f"### ✏️ Editing {day.get('day', 'Day')}")
    focus = st.text_input("Focus", value=day.get("focus", ""), key=f"edit_focus_{day_index}")

    rows = [
        {"Exercise": ex.get("name", ""), "Sets": str(ex.get("sets", "")), "Reps": str(ex.get("reps", "")),
         "Notes": ex.get("notes", "")}
        if isinstance(ex, dict) else {"Exercise": str(ex), "Sets": "", "Reps": "", "Notes": ""}
        for ex in day.get("exercises", [])
    ]
    edited = st.data_editor(
        pd.DataFrame(rows, columns=_EDITOR_COLUMNS),
        key=f"edit_table_{day_index}",
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "Exercise": st.column_config.TextColumn(required=True, width="medium"),
            "Sets": st.column_config.TextColumn(width="small", help="e.g. 3"),
            "Reps": st.column_config.TextColumn(width="small", help="e.g. 8-12 or 30s"),
            "Notes": st.column_config.TextColumn(width="large"),
        },
    )
    st.caption("Tap a cell to change it. Add an exercise in the empty row at the bottom; "
               "to remove one, select its row and press the 🗑️ icon.")

    save_col, cancel_col = st.columns(2)
    if save_col.button("💾 Save Changes", type="primary", key=f"edit_save_{day_index}", use_container_width=True):
        exercises = _exercises_from_editor(edited)
        if not exercises:
            st.error("Add at least one exercise before saving.", icon="🚨")
            return
        new_plan = copy.deepcopy(plan)
        new_day = new_plan["workout_plan"]["weekly_split"][day_index]
        new_day["focus"] = focus.strip()
        new_day["exercises"] = exercises
        st.session_state.editing_day = None
        if new_plan != plan:
            st.session_state.plan = new_plan
            st.session_state.unchecked_plan = new_plan  # Shows the safety-check prompt
            st.session_state.flash_message = f"✏️ Saved your changes to {day.get('day', 'this day')}."
        st.rerun()
    if cancel_col.button("Cancel", key=f"edit_cancel_{day_index}", use_container_width=True):
        st.session_state.editing_day = None
        st.rerun()


def _exercises_from_editor(edited: pd.DataFrame) -> List[Dict[str, Any]]:
    def cell(value: Any) -> str:
        return "" if value is None or pd.isna(value) else str(value).strip()

    exercises = []
    for row in edited.to_dict("records"):
        name = cell(row.get("Exercise"))
        if not name:
            continue  # Blank rows are ignored
        sets = cell(row.get("Sets"))
        exercises.append({
            "name": name,
            "sets": int(sets) if sets.isdigit() else sets,
            "reps": cell(row.get("Reps")),
            "notes": cell(row.get("Notes")),
        })
    return exercises


def _render_safety_check_prompt(plan: Dict[str, Any]) -> None:
    """
    After the user edits exercises themselves, offers to run the same Safety Audit that
    AI-made changes get. Disappears once the plan changes again or is checked.
    """
    if st.session_state.get("unchecked_plan") is not plan:
        return
    st.info(
        "You've edited your workouts. Your own edits aren't safety-checked automatically; "
        "run a check to make sure they still suit your injuries and experience.",
        icon="🛡️",
    )
    if st.button("🛡️ Safety-check my plan", key="safety_check_edits"):
        with st.spinner("Running the safety check..."):
            try:
                checked = HealthForgePlanner().safety_check(st.session_state.profile, copy.deepcopy(plan))
                st.session_state.plan = checked
                st.session_state.flash_message = (
                    "🛡️ The safety check flagged a concern. See the warning above your plan."
                    if failed_safety_audit(checked) else "🛡️ Your edited plan passed the safety check."
                )
                st.rerun()
            except Exception as e:
                show_error_alert("safety-check your plan", e)


def describe_swap_item(plan: Dict[str, Any], item_id: str) -> str:
    """What an exercise ("d0e1") or meal ("m1") id currently is, e.g. "Goblet Squat"."""
    try:
        if item_id.startswith("d"):
            d, e = map(int, item_id[1:].split("e"))
            ex = plan["workout_plan"]["weekly_split"][d]["exercises"][e]
            return ex.get("name", "Exercise") if isinstance(ex, dict) else str(ex)
        meal = plan["nutrition_plan"]["daily_structure"][int(item_id[1:])]
        return f"{meal.get('meal', 'Meal')}: {meal.get('example', '')}" if isinstance(meal, dict) else str(meal)
    except (KeyError, IndexError, ValueError):
        return item_id


def render_swap_choices(
    plan: Dict[str, Any], options: Dict[str, List[Dict[str, Any]]], version: int
) -> Tuple[str | None, Dict[str, Dict[str, Any]]]:
    """
    Shows the replacement options for each item. Returns ("apply", {id: chosen option}),
    ("cancel", {}), or (None, {}) while the user is still choosing.
    """
    choices = {}
    with st.container(border=True):
        st.markdown("### 🔄 Choose Your Replacements")
        for item_id, item_options in options.items():
            current = describe_swap_item(plan, item_id)
            if item_id.startswith("d"):
                labels = [f"**{o['name']}** · {o.get('sets', '')} × {o.get('reps', '')}" for o in item_options]
                captions = [o.get("notes", "") for o in item_options]
            else:
                labels = [f"**{o['example']}**" for o in item_options]
                captions = [
                    o.get("notes", "") + (f" Adds to grocery list: {', '.join(o['grocery_additions'])}."
                                          if o.get("grocery_additions") else "")
                    for o in item_options
                ]
            labels.append("Keep it as is")
            captions.append("")
            pick = st.radio(
                f"Replace **{current}** with:",
                range(len(labels)),
                format_func=lambda i, labels=labels: labels[i],
                captions=captions,
                key=f"swap_choice_{item_id}_v{version}",
            )
            if pick < len(item_options):
                choices[item_id] = item_options[pick]

        apply_col, cancel_col = st.columns(2)
        if apply_col.button("✅ Apply My Choices", type="primary", key="swap_apply", use_container_width=True):
            return "apply", choices
        if cancel_col.button("Cancel", key="swap_cancel", use_container_width=True):
            return "cancel", {}
    return None, {}


def _render_nutrition_tab(nutrition_plan: Dict[str, Any]) -> None:
    philosophy = nutrition_plan.get("philosophy", "")
    daily_structure = nutrition_plan.get("daily_structure", [])
    grocery_list = nutrition_plan.get("grocery_list", [])

    if philosophy:
        st.markdown("### Nutrition Philosophy")
        st.write(philosophy)

    if daily_structure:
        st.markdown("### Daily Meal Structure")
        st.caption(
            "☑️ Tick any meals you'd like to replace, then click "
            "**Find Replacements** below the plan to choose from suggestions."
        )
        for m, meal in enumerate(daily_structure):
            if not isinstance(meal, dict):
                st.markdown(f"- {meal}")
                continue
            st.checkbox(f"**{meal.get('meal', 'Meal')}**", key=_meal_swap_key(m, meal))
            st.write(f"- Example: {meal.get('example', '')}")
            st.write(f"- Notes: {meal.get('notes', '')}")

    if grocery_list:
        st.markdown("### Grocery List")
        for item in grocery_list:
            st.markdown(f"- {item}")


def _render_habits_tab(habits: Dict[str, Any]) -> None:
    sleep = habits.get("sleep", [])
    stress = habits.get("stress_management", [])
    daily = habits.get("daily_habits", [])

    if sleep:
        st.markdown("### Sleep")
        for tip in sleep:
            st.markdown(f"- {tip}")

    if stress:
        st.markdown("### Stress Management")
        for tip in stress:
            st.markdown(f"- {tip}")

    if daily:
        st.markdown("### Daily Habits")
        for tip in daily:
            st.markdown(f"- {tip}")

    if not (sleep or stress or daily):
        st.info("No habit or lifestyle suggestions available.")


def _render_disclaimers_tab(disclaimers: Any) -> None:
    if not disclaimers:
        st.info("No disclaimers provided.")
        return

    st.markdown("### Safety & Disclaimers")
    for d in disclaimers:
        st.markdown(f"- {d}")


def render_nutrition_from_image() -> Dict[str, Any] | None:
    """
    Renders an image upload interface for extracting nutrition data.
    Returns extracted macro data or None if no image processed.
    """
    st.markdown("---")
    st.subheader("📸 Log Meal from Photo (Beta)")
    st.write(
        "Upload a photo of a food label or your meal. Our AI will extract macros "
        "and help adjust your nutrition plan."
    )

    uploaded_file = st.file_uploader(
        "Choose a food image...",
        type=["jpg", "jpeg", "png"],
        key="nutrition_image_upload",
    )

    if uploaded_file is not None:
        # Display the image
        st.image(uploaded_file, caption="Uploaded meal photo", use_container_width=True)

        if st.button("Extract Nutrition Info", key="extract_macros_btn"):
            with st.spinner("Analyzing image with AI vision..."):
                try:
                    from services.vision_client import GeminiVisionClient
                    from config import GEMINI_API_KEY

                    if not GEMINI_API_KEY:
                        st.error(
                            "**Meal photo logging isn't available right now.** "
                            "The app isn't fully configured (missing API key).",
                            icon="🚨",
                        )
                        return None

                    # Read image bytes
                    image_bytes = uploaded_file.getvalue()
                    image_type = f"image/{uploaded_file.type.split('/')[-1]}"

                    # Extract macros
                    vision_client = GeminiVisionClient(GEMINI_API_KEY)
                    result = vision_client.extract_macros_from_image(
                        image_bytes, image_type
                    )

                    # Display results
                    if "error" in result:
                        st.warning(
                            f"**Couldn't analyze this photo.** {result['error']}\n\n"
                            "You can also describe the meal in Coach Feedback below.",
                            icon="⚠️",
                        )
                        return None

                    # Show extracted data
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Protein", f"{result['protein_g']:.1f}g")
                        st.metric("Fat", f"{result['fat_g']:.1f}g")
                    with col2:
                        st.metric("Carbs", f"{result['carbs_g']:.1f}g")
                        st.metric("Calories", f"{result['calories']:.0f}")

                    st.write(f"**Food**: {result['food_description']}")
                    st.write(
                        f"**Confidence**: {result['confidence']} "
                        f"({result.get('notes', 'No notes')})"
                    )

                    # Store in session state so it survives the next rerun
                    st.session_state.extracted_macros = result

                    # Return macro data for plan adjustment
                    return result

                except Exception as e:
                    show_error_alert("analyze this photo", e)
                    return None

    return None


def render_meal_journal(meal_log: List[Dict[str, Any]]) -> None:
    """
    Renders the daily meal journal and running macro totals.
    meal_log is a list of dicts with keys:
      timestamp, food_description, calories, protein_g, carbs_g, fat_g, confidence, notes
    """
    st.markdown("---")
    st.subheader("📓 Today's Meal Journal")

    if not meal_log:
        st.info("No meals logged yet. Upload a food photo above and click **Update Plan with These Macros** to start tracking.")
        return

    # ── Clear log button ──────────────────────────────────────────────────────
    if st.button("🗑️ Clear Log", key="clear_meal_log_btn"):
        st.session_state.meal_log = []
        st.rerun()

    # ── Daily running totals ──────────────────────────────────────────────────
    total_cal     = sum(m.get("calories",  0) for m in meal_log)
    total_protein = sum(m.get("protein_g", 0) for m in meal_log)
    total_carbs   = sum(m.get("carbs_g",   0) for m in meal_log)
    total_fat     = sum(m.get("fat_g",     0) for m in meal_log)

    st.markdown("#### Daily Totals")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔥 Calories",  f"{total_cal:.0f} kcal")
    c2.metric("💪 Protein",   f"{total_protein:.1f} g")
    c3.metric("🌾 Carbs",     f"{total_carbs:.1f} g")
    c4.metric("🥑 Fat",       f"{total_fat:.1f} g")

    st.caption(f"{len(meal_log)} meal(s) logged today")

    # ── Per-meal cards ────────────────────────────────────────────────────────
    st.markdown("#### Logged Meals")
    for i, meal in enumerate(reversed(meal_log)):  # most recent first
        label = f"{meal.get('timestamp', '—')}  ·  {meal.get('food_description', 'Unknown food')}  ·  {meal.get('calories', 0):.0f} kcal"
        with st.expander(label, expanded=(i == 0)):
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Protein", f"{meal.get('protein_g', 0):.1f} g")
            mc2.metric("Carbs",   f"{meal.get('carbs_g',   0):.1f} g")
            mc3.metric("Fat",     f"{meal.get('fat_g',     0):.1f} g")
            confidence = meal.get("confidence", "—")
            notes      = meal.get("notes", "")
            st.caption(f"Confidence: **{confidence}**{'  ·  ' + notes if notes else ''}")

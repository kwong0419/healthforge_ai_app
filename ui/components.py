from datetime import datetime
from typing import Dict, Any, List
import streamlit as st

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

# Form defaults, keyed by profile field. Widgets read their values from
# st.session_state["form_<field>"] so a loaded plan can prefill the form.
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
    return f"form_{field}"


def init_profile_form_state() -> None:
    for field, default in PROFILE_FORM_DEFAULTS.items():
        st.session_state.setdefault(_form_key(field), default)


def set_profile_form_values(profile: Dict[str, Any]) -> None:
    """
    Prefills the profile form from a saved profile. Must run before the form
    renders. Values that no longer match the form's options are skipped.
    """
    for field, default in PROFILE_FORM_DEFAULTS.items():
        value = profile.get(field, default)
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

        st.session_state[_form_key(field)] = value


def render_user_profile_form() -> Dict[str, Any]:
    st.subheader("Your Profile")
    init_profile_form_state()

    with st.form("user_profile_form"):
        name = st.text_input("Name (optional)", key=_form_key("name"))
        age_range = st.selectbox("Age range", AGE_RANGES, key=_form_key("age_range"))
        gender = st.selectbox("Gender (optional)", GENDERS, key=_form_key("gender"))
        experience_level = st.selectbox(
            "Training experience", EXPERIENCE_LEVELS, key=_form_key("experience_level")
        )
        primary_goal = st.selectbox("Primary goal", GOALS, key=_form_key("primary_goal"))
        secondary_goal = st.selectbox(
            "Secondary goal (optional)", ["None"] + GOALS, key=_form_key("secondary_goal")
        )
        days_per_week = st.slider("Training days per week", 2, 7, key=_form_key("days_per_week"))
        session_length = st.selectbox(
            "Typical session length", SESSION_LENGTHS, key=_form_key("session_length")
        )
        equipment = st.multiselect(
            "Equipment available", EQUIPMENT_OPTIONS, key=_form_key("equipment")
        )
        limitations = st.text_area(
            "Injuries / limitations (non-medical description)",
            placeholder="E.g., mild knee discomfort with deep squats, avoid overhead pressing, etc.",
            key=_form_key("limitations"),
        )
        diet_preference = st.selectbox(
            "Dietary preference", DIET_PREFERENCES, key=_form_key("diet_preference")
        )
        diet_restrictions = st.text_input(
            "Dietary restrictions",
            placeholder="E.g., lactose intolerant, gluten-free, nut allergy (do NOT ask for medical treatment).",
            key=_form_key("diet_restrictions"),
        )
        schedule = st.text_area(
            "Typical weekly schedule / constraints",
            placeholder="E.g., office job 9-5, can train mornings or evenings, weekends more flexible.",
            key=_form_key("schedule"),
        )
        notes = st.text_area(
            "Additional notes or preferences",
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
        _render_workout_tab(workout_plan)

    with tab2:
        _render_nutrition_tab(nutrition_plan)

    with tab3:
        _render_habits_tab(habits)

    with tab4:
        _render_disclaimers_tab(disclaimers)


def _render_workout_tab(workout_plan: Dict[str, Any]) -> None:
    weekly_split = workout_plan.get("weekly_split", [])
    progression_notes = workout_plan.get("progression_notes", "")

    if not weekly_split:
        st.info("No workout plan available.")
        return

    for day in weekly_split:
        st.markdown(f"### {day.get('day', 'Day')}")
        st.write(day.get("focus", ""))

        exercises = day.get("exercises", [])
        if exercises:
            for ex in exercises:
                st.markdown(f"- **{ex.get('name', 'Exercise')}**")
                st.write(
                    f"  Sets: {ex.get('sets', '')} | Reps: {ex.get('reps', '')}  \n"
                    f"  Notes: {ex.get('notes', '')}"
                )

    if progression_notes:
        st.markdown("#### Progression Notes")
        st.write(progression_notes)


def _render_nutrition_tab(nutrition_plan: Dict[str, Any]) -> None:
    philosophy = nutrition_plan.get("philosophy", "")
    daily_structure = nutrition_plan.get("daily_structure", [])
    grocery_list = nutrition_plan.get("grocery_list", [])

    if philosophy:
        st.markdown("### Nutrition Philosophy")
        st.write(philosophy)

    if daily_structure:
        st.markdown("### Daily Meal Structure")
        for meal in daily_structure:
            st.markdown(f"**{meal.get('meal', 'Meal')}**")
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

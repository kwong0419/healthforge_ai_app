from typing import Dict, Any
import streamlit as st


def render_header(app_name: str, tagline: str) -> None:
    st.title(app_name)
    st.caption(tagline)


def render_user_profile_form() -> Dict[str, Any]:
    st.subheader("Your Profile")

    with st.form("user_profile_form"):
        name = st.text_input("Name (optional)")
        age_range = st.selectbox(
            "Age range",
            ["18-24", "25-34", "35-44", "45-54", "55+"],
            index=1,
        )
        gender = st.selectbox(
            "Gender (optional)",
            ["Prefer not to say", "Female", "Male", "Non-binary", "Other"],
            index=0,
        )
        experience_level = st.selectbox(
            "Training experience",
            ["Beginner", "Intermediate", "Advanced"],
            index=0,
        )
        primary_goal = st.selectbox(
            "Primary goal",
            [
                "Build muscle",
                "Lose fat",
                "Improve general health",
                "Increase strength",
                "Improve endurance",
            ],
            index=0,
        )
        secondary_goal = st.selectbox(
            "Secondary goal (optional)",
            [
                "None",
                "Build muscle",
                "Lose fat",
                "Improve general health",
                "Increase strength",
                "Improve endurance",
            ],
            index=0,
        )
        days_per_week = st.slider("Training days per week", 2, 7, 4)
        session_length = st.selectbox(
            "Typical session length",
            ["30-45 minutes", "45-60 minutes", "60-75 minutes", "75+ minutes"],
            index=1,
        )
        equipment = st.multiselect(
            "Equipment available",
            [
                "None (bodyweight only)",
                "Dumbbells",
                "Barbell",
                "Machines",
                "Resistance bands",
                "Kettlebells",
                "Cable stack",
            ],
            default=["None (bodyweight only)"],
        )
        limitations = st.text_area(
            "Injuries / limitations (non-medical description)",
            placeholder="E.g., mild knee discomfort with deep squats, avoid overhead pressing, etc.",
        )
        diet_preference = st.selectbox(
            "Dietary preference",
            [
                "No specific preference",
                "High-protein omnivore",
                "Vegetarian",
                "Vegan",
                "Pescatarian",
                "Halal",
                "Kosher",
            ],
            index=1,
        )
        diet_restrictions = st.text_input(
            "Dietary restrictions",
            placeholder="E.g., lactose intolerant, gluten-free, nut allergy (do NOT ask for medical treatment).",
        )
        schedule = st.text_area(
            "Typical weekly schedule / constraints",
            placeholder="E.g., office job 9-5, can train mornings or evenings, weekends more flexible.",
        )
        notes = st.text_area(
            "Additional notes or preferences",
            placeholder="E.g., prefer dumbbells over barbells, like group classes, hate running, etc.",
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

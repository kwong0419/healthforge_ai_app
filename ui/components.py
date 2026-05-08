from datetime import datetime
from typing import Dict, Any, List
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
                            "❌ Gemini API key not configured. "
                            "Please add GEMINI_API_KEY to your environment."
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
                        st.warning(f"⚠️ {result['error']}")
                        st.info("Try a clearer image or manually adjust your plan.")
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

                except ImportError as e:
                    st.error(f"Missing dependency: {str(e)}")
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
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

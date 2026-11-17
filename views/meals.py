"""
The Meals page: log a meal from a photo, let the coach adjust the rest of the day's
meals, and see today's meal journal.
"""
from datetime import datetime

import streamlit as st

from ui.alerts import show_error_alert
from ui.components import render_nutrition_from_image, render_meal_journal
from views.shared import apply_feedback, show_coach_reply


def meals_view() -> None:
    if not st.session_state.plan:
        from views.nav import profile_page
        st.info("You don't have a plan yet. Fill out your profile to get one.")
        st.page_link(profile_page(), label="Go to your profile", icon="👤")
        return

    # After "Update Plan with These Macros", the coach's reply appears here.
    show_coach_reply()

    # Vision-based nutrition logging
    render_nutrition_from_image()
    extracted_macros = st.session_state.extracted_macros
    if extracted_macros and extracted_macros.get("confidence") != "low":
        st.markdown("---")
        st.subheader("Adjust Plan with Extracted Nutrition")

        if st.button("Update Plan with These Macros", key="update_with_macros_btn"):
            with st.spinner("Updating your plan based on extracted nutrition..."):
                try:
                    # Build feedback message from extracted macros
                    macro_feedback = (
                        f"I just logged a meal with approximately: "
                        f"{extracted_macros['protein_g']:.0f}g protein, "
                        f"{extracted_macros['carbs_g']:.0f}g carbs, "
                        f"{extracted_macros['fat_g']:.0f}g fat "
                        f"({extracted_macros['calories']:.0f} calories). "
                        f"Please adjust my remaining meals for today accordingly. "
                        f"Food logged: {extracted_macros['food_description']}"
                    )
                    food = extracted_macros.get("food_description", "your meal")
                    apply_feedback(macro_feedback, asked=f"Adjust my remaining meals for today — I just ate {food}.")

                    # Append to meal journal
                    st.session_state.meal_log.append({
                        "timestamp": datetime.now().strftime("%H:%M"),
                        "food_description": extracted_macros.get("food_description", "Unknown"),
                        "calories":  extracted_macros.get("calories",  0),
                        "protein_g": extracted_macros.get("protein_g", 0),
                        "carbs_g":   extracted_macros.get("carbs_g",   0),
                        "fat_g":     extracted_macros.get("fat_g",     0),
                        "confidence": extracted_macros.get("confidence", "low"),
                        "notes":     extracted_macros.get("notes", ""),
                    })
                    st.session_state.extracted_macros = None  # clear after use
                    st.rerun()
                except Exception as e:
                    show_error_alert("update your plan with this meal", e)

    render_meal_journal(st.session_state.meal_log)

import streamlit as st
import json
import re
import unicodedata
from datetime import datetime
from typing import List

# Must be the very first Streamlit command
st.set_page_config(
    page_title="HealthForge AI",
    page_icon="💪",
    layout="wide",
)

from config import APP_NAME, APP_TAGLINE
from services.planner import HealthForgePlanner, failed_safety_audit
from services.plan_storage import serialize_plan, load_plan_file, PlanFileError
from services.pdf_export import build_plan_pdf
from ui.alerts import show_error_alert
from ui.components import render_header, render_user_profile_form, render_plan, render_nutrition_from_image, render_meal_journal, set_profile_form_values, selected_swap_ids, selected_meal_swap_ids


def init_session_state() -> None:
    defaults = {
        "plan": None,
        "chat_history": [],
        "profile": None,
        "flash_message": None,
        "meal_log": [],
        "extracted_macros": None,
        "macro_logged_meal": None,
        "loaded_plan_file_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_load_plan(location: str) -> None:
    """
    Uploader that restores a previously saved plan: on the main page when no plan is
    loaded (the sidebar is hidden on phones), in the sidebar otherwise. Runs before the
    profile form so the form can be prefilled with the saved profile.
    """
    if location == "main":
        st.markdown("### 📂 Already have a plan?")
        label = "Upload the PDF or plan file you downloaded from HealthForge to pick up where you left off."
    else:
        st.markdown("### Load a Saved Plan")
        label = "Upload a plan PDF or plan file you downloaded from HealthForge"
    uploaded = st.file_uploader(label, type=["pdf", "json"], key=f"plan_file_uploader_{location}")
    # The uploader keeps its file across reruns, so only load each file once.
    if uploaded is None or uploaded.file_id == st.session_state.loaded_plan_file_id:
        return

    st.session_state.loaded_plan_file_id = uploaded.file_id
    try:
        saved = load_plan_file(uploaded.getvalue())
    except PlanFileError as e:
        st.error(f"**Couldn't load that plan.** {e}", icon="🚨")
        return

    st.session_state.plan = saved["plan"]
    st.session_state.profile = saved["profile"]
    st.session_state.meal_log = saved["meal_log"]
    st.session_state.chat_history = saved["chat_history"]
    st.session_state.extracted_macros = None
    set_profile_form_values(saved["profile"])
    st.session_state.flash_message = "📂 Saved plan loaded."
    st.rerun()  # Redraw so the uploader moves from the main page to the sidebar


def apply_feedback(feedback: str) -> None:
    """
    Sends feedback to the coach, records the exchange, and swaps in the updated plan.
    """
    planner = HealthForgePlanner()
    new_plan = planner.update_plan(
        user_profile=st.session_state.profile,
        current_plan=st.session_state.plan,
        chat_history=st.session_state.chat_history,
        new_feedback=feedback
    )

    # Update history to store this exchange for next time
    st.session_state.chat_history.append({"role": "assistant", "content": json.dumps(st.session_state.plan)})
    st.session_state.chat_history.append({"role": "user", "content": feedback})

    # Keep history short (last 5 interactions = 10 messages)
    if len(st.session_state.chat_history) > 10:
        st.session_state.chat_history = st.session_state.chat_history[-10:]

    st.session_state.plan = new_plan


@st.cache_data(max_entries=20, show_spinner=False)
def cached_plan_pdf(plan: dict, profile: dict | None, meal_log: list, chat_history: list) -> bytes:
    # Download buttons need their data on every rerun; only rebuild when the plan changes.
    # The PDF carries the full save data, so it can be uploaded later to reload the plan.
    save_data = serialize_plan(profile=profile, plan=plan, meal_log=meal_log, chat_history=chat_history)
    return build_plan_pdf(plan, profile, save_data=save_data)


def plan_file_stem(profile: dict | None) -> str:
    """E.g. "healthforge-plan-jose-nunez-2026-10-14" (name omitted if not given)."""
    name = (profile or {}).get("name") or ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return "-".join(p for p in ["healthforge-plan", slug, f"{datetime.now():%Y-%m-%d}"] if p)


def _count_label(count: int, noun: str) -> List[str]:
    """E.g. ["2 exercises"], or [] for none."""
    return [f"{count} {noun}{'' if count == 1 else 's'}"] if count else []


def render_plan_actions() -> None:
    """
    Download or save the current plan, or ask for a new take on it.
    """
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        try:
            st.download_button(
                "📄 Download PDF",
                data=cached_plan_pdf(
                    st.session_state.plan,
                    st.session_state.profile,
                    st.session_state.meal_log,
                    st.session_state.chat_history,
                ),
                file_name=f"{plan_file_stem(st.session_state.profile)}.pdf",
                mime="application/pdf",
                help="A clean, printable copy of your plan. You can also upload this PDF "
                "to HealthForge later to reload your plan.",
                type="primary",
                use_container_width=True,
            )
        except Exception as e:
            show_error_alert("create the PDF of your plan", e)

    with col2:
        st.download_button(
            "💾 Save Plan File",
            data=serialize_plan(
                profile=st.session_state.profile,
                plan=st.session_state.plan,
                meal_log=st.session_state.meal_log,
                chat_history=st.session_state.chat_history,
            ),
            file_name=f"{plan_file_stem(st.session_state.profile)}.json",
            # A generic type makes phone browsers download the file instead of opening it
            # as a page (which saves it as .html and breaks reloading).
            mime="application/octet-stream",
            help="Save this plan to load it back into HealthForge later.",
            use_container_width=True,
        )

    with col3:
        regenerate = st.button(
            "🎲 Generate a Different Version",
            help="Build a brand-new plan from the same profile.",
            use_container_width=True,
        )

    exercise_ids = selected_swap_ids(st.session_state.plan)
    meal_ids = selected_meal_swap_ids(st.session_state.plan)
    picked = _count_label(len(exercise_ids), "exercise") + _count_label(len(meal_ids), "meal")
    with col4:
        swap = st.button(
            "🔄 Swap Selected" + (f" ({', '.join(picked)})" if picked else ""),
            help="Replace only the exercises and meals you ticked; everything else stays the same."
            if picked else "Tick exercises (Workout Plan tab) or meals (Nutrition tab) to choose what to swap.",
            disabled=not picked,
            use_container_width=True,
        )

    if regenerate:
        with st.spinner("Generating a different version of your plan..."):
            try:
                planner = HealthForgePlanner()
                st.session_state.plan = planner.build_full_plan(st.session_state.profile)
                st.session_state.chat_history = []  # New plan, fresh conversation
                st.session_state.flash_message = "🎲 Here's a different version of your plan."
                st.rerun()
            except Exception as e:
                show_error_alert("generate a different version of your plan", e)

    if swap:
        with st.spinner(f"Finding replacements for {' and '.join(picked)}..."):
            try:
                planner = HealthForgePlanner()
                st.session_state.plan, changes = planner.swap_selected(
                    st.session_state.profile, st.session_state.plan, exercise_ids, meal_ids
                )
                st.session_state.flash_message = "🔄 Swapped: " + "; ".join(
                    f"{old} → **{new}**" for old, new in changes
                )
                st.rerun()
            except Exception as e:
                show_error_alert("swap the selected items", e)


def main() -> None:
    render_header(APP_NAME, APP_TAGLINE)
    init_session_state()

    with st.sidebar:
        st.markdown("### About")
        st.write(
            "HealthForge AI is a portfolio-grade fitness, nutrition, and habit coach "
            "powered by GPT-OSS on Groq. It demonstrates end-to-end LLM integration, "
            "prompt engineering, and a Streamlit front end."
        )
        st.markdown("---")
        st.write("**Note:** This is not medical advice. Always consult a professional for health concerns.")
        if st.session_state.plan:
            st.markdown("---")
            render_load_plan("sidebar")

    if not st.session_state.plan:
        with st.container(border=True):
            render_load_plan("main")

    profile, submitted = render_user_profile_form()

    if submitted:
        with st.spinner("Generating your personalized plan with GPT-OSS on Groq..."):
            try:
                planner = HealthForgePlanner()
                st.session_state.plan = planner.build_full_plan(profile)
                st.session_state.profile = profile
                st.session_state.chat_history = [] # Reset history on new plan
            except Exception as e:
                show_error_alert("generate your plan", e)
    elif not st.session_state.plan:
        st.info(
            "Fill out your profile and click **Generate Plan** to get started, "
            "or upload a saved plan above."
        )

    if st.session_state.plan:
        if st.session_state.flash_message:
            st.success(st.session_state.flash_message)
            st.session_state.flash_message = None

        if st.session_state.macro_logged_meal:
            food = st.session_state.macro_logged_meal
            st.success(f"🍽️ Meal logged: **{food}** — your remaining meals have been adjusted.")
            st.session_state.macro_logged_meal = None

        if failed_safety_audit(st.session_state.plan):
            st.warning(
                "**This plan didn't pass the automated safety check.** "
                "Review it carefully, especially around your injuries and limitations — "
                "see the Disclaimers tab for the specific concern. You can ask the coach "
                "to fix it below, or use **Generate a Different Version**.",
                icon="⚠️",
            )

        render_plan(st.session_state.plan)
        render_plan_actions()

        # Vision-based nutrition logging
        render_nutrition_from_image()
        extracted_macros = st.session_state.extracted_macros
        if extracted_macros and extracted_macros.get("confidence") != "low":
            st.markdown("---")
            st.subheader("Adjust Plan with Extracted Nutrition")
            
            if st.button("Update Plan with These Macros", key="update_with_macros_btn"):
                with st.spinner("Updating your plan based on extracted nutrition..."):
                    try:
                        planner = HealthForgePlanner()
                        
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
                        
                        new_plan = planner.update_plan(
                            user_profile=st.session_state.profile,
                            current_plan=st.session_state.plan,
                            chat_history=st.session_state.chat_history,
                            new_feedback=macro_feedback
                        )
                        
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

                        # Update history
                        st.session_state.chat_history.append({"role": "assistant", "content": json.dumps(st.session_state.plan)})
                        st.session_state.chat_history.append({"role": "user", "content": macro_feedback})

                        # Keep history short
                        if len(st.session_state.chat_history) > 10:
                            st.session_state.chat_history = st.session_state.chat_history[-10:]

                        st.session_state.plan = new_plan
                        st.session_state.macro_logged_meal = extracted_macros.get("food_description", "your meal")
                        st.session_state.extracted_macros = None  # clear after use
                        st.rerun()
                    except Exception as e:
                        show_error_alert("update your plan with this meal", e)
        
        render_meal_journal(st.session_state.meal_log)

        st.markdown("---")
        st.subheader("Coach Feedback")
        st.write("Tell your AI Coach what you'd like to change (e.g., 'Deadlifts were too heavy', 'I don't eat broccoli').")
        
        feedback = st.chat_input("Enter your feedback here...")
        if feedback:
            with st.spinner("Updating your plan..."):
                try:
                    apply_feedback(feedback)
                    st.session_state.flash_message = "✅ Your plan has been successfully updated based on your feedback!"
                    st.rerun()
                except Exception as e:
                    show_error_alert("update your plan with your feedback", e)


if __name__ == "__main__":
    main()

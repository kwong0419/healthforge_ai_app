"""
The Profile page. Before there's a plan it's the start page (load a saved plan, or fill
in the profile to generate one); after, it's where to change details, load another
plan, or start over.
"""
import streamlit as st

from config import APP_NAME, APP_TAGLINE
from services.planner import HealthForgePlanner
from ui.alerts import show_error_alert
from ui.components import render_header, render_user_profile_form
from views.shared import go_to_plan, render_load_plan, start_over


def _generate(profile: dict) -> None:
    with st.spinner("Generating your personalized plan with GPT-OSS on Groq..."):
        try:
            planner = HealthForgePlanner()
            st.session_state.plan = planner.build_full_plan(profile)
        except Exception as e:
            show_error_alert("generate your plan", e)
            return
    st.session_state.profile = profile
    st.session_state.chat_history = []  # New plan, fresh conversation
    st.session_state.coach_reply = None
    st.session_state.flash_message = "✨ Your plan is ready!"
    go_to_plan()


def profile_view() -> None:
    has_plan = bool(st.session_state.plan)

    if not has_plan:
        render_header(APP_NAME, APP_TAGLINE)
        with st.container(border=True):
            st.markdown("### 📂 Already have a plan?")
            render_load_plan(
                "Upload the PDF or plan file you downloaded from HealthForge to pick up where you left off."
            )
        profile, submitted = render_user_profile_form()
        if submitted:
            _generate(profile)
        return

    profile, submitted = render_user_profile_form(
        submit_label="Generate a New Plan",
        caption="Change your details and generate a new plan. This replaces your current plan.",
    )
    if submitted:
        _generate(profile)

    st.markdown("---")
    st.markdown("### 📂 Load a saved plan")
    render_load_plan("Upload a plan PDF or plan file you downloaded from HealthForge")

    st.markdown("---")
    st.markdown("### 🗑️ Start over")
    st.caption("Your plan is remembered on this device, so it's here when you come back.")
    if st.button("Start Over", help="Clear this plan from the page and from this device."):
        start_over()

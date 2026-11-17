"""
The plan page: the overview and tabs, swapping exercises or meals, and downloading
or regenerating the plan.
"""
import re
import unicodedata
from datetime import datetime
from typing import List

import streamlit as st

from services.planner import HealthForgePlanner, failed_safety_audit
from services.plan_storage import serialize_plan
from services.pdf_export import build_plan_pdf
from ui.alerts import show_error_alert
from ui.components import render_plan, selected_swap_ids, selected_meal_swap_ids, clear_swap_selection, render_swap_choices


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
    col1, col2, col3 = st.columns(3)

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

    if regenerate:
        with st.spinner("Generating a different version of your plan..."):
            try:
                planner = HealthForgePlanner()
                st.session_state.plan = planner.build_full_plan(st.session_state.profile)
                st.session_state.chat_history = []  # New plan, fresh conversation
                st.session_state.coach_reply = None
                st.session_state.flash_message = "🎲 Here's a different version of your plan."
                st.rerun()
            except Exception as e:
                show_error_alert("generate a different version of your plan", e)


def render_swap_section() -> None:
    """
    Once exercises or meals are ticked in swap mode, asks the AI coach for replacement
    options and then shows the choices.
    """
    pending = st.session_state.get("swap_options")
    if pending and pending["plan"] is st.session_state.plan:
        render_pending_swap_choices()
        return

    exercise_ids = selected_swap_ids(st.session_state.plan)
    meal_ids = selected_meal_swap_ids(st.session_state.plan)
    picked = _count_label(len(exercise_ids), "exercise") + _count_label(len(meal_ids), "meal")
    if not picked:
        return

    with st.container(border=True):
        st.markdown(f"#### 🔄 Replace {' and '.join(picked)}")
        preferences = st.text_input(
            "Optional: what should the replacements be like?",
            placeholder="e.g. dumbbells only, no jumping, more unilateral work, quick to prep",
            key="swap_preferences",
        )
        with st.container(key="hf_inline_swap_find_actions"):
            clear_col, find_col = st.columns([1, 1.6])
            clear_col.button("Clear ticks", on_click=clear_swap_selection, use_container_width=True)
            find_options = find_col.button("Find replacements", type="primary", use_container_width=True)

    if find_options:
        with st.spinner(f"Finding options for {' and '.join(picked)}..."):
            try:
                planner = HealthForgePlanner()
                options = planner.find_swap_options(
                    st.session_state.profile, st.session_state.plan, exercise_ids, meal_ids, preferences
                )
                st.session_state.swap_options = {
                    "plan": st.session_state.plan,  # Options only apply to the plan they were made for
                    "options": options,
                }
                # A new version gives the choice lists fresh widgets, so old picks don't carry over.
                st.session_state.swap_options_version = st.session_state.get("swap_options_version", 0) + 1
                st.rerun()
            except Exception as e:
                show_error_alert("find replacement options", e)


def render_pending_swap_choices() -> None:
    """
    Shows the replacement options found by Find Replacements and applies the user's picks.
    """
    pending = st.session_state.get("swap_options")
    if not pending or pending["plan"] is not st.session_state.plan:
        return  # Nothing found yet, or the plan has changed since

    action, choices = render_swap_choices(
        st.session_state.plan, pending["options"], st.session_state.swap_options_version
    )
    if action == "cancel" or (action == "apply" and not choices):
        st.session_state.swap_options = None
        st.rerun()
    if action != "apply":
        return

    with st.spinner("Applying your choices and running the safety check..."):
        try:
            planner = HealthForgePlanner()
            st.session_state.plan, changes = planner.apply_swap_choices(
                st.session_state.profile, st.session_state.plan, choices
            )
            st.session_state.swap_options = None
            clear_swap_selection()
            st.session_state.flash_message = "🔄 Swapped: " + "; ".join(
                f"{old} → **{new}**" for old, new in changes
            )
            st.rerun()
        except Exception as e:
            show_error_alert("apply your choices", e)


def plan_view() -> None:
    if not st.session_state.plan:
        from views.nav import profile_page
        st.info("You don't have a plan yet. Fill out your profile to get one.")
        st.page_link(profile_page(), label="Go to your profile", icon="👤")
        return

    if failed_safety_audit(st.session_state.plan):
        st.warning(
            "**This plan didn't pass the automated safety check.** "
            "Review it carefully, especially around your injuries and limitations — "
            "see the Disclaimers tab for the specific concern. You can ask the coach "
            "to fix it on the **Coach** page, or use **Generate a Different Version**.",
            icon="⚠️",
        )

    render_plan(st.session_state.plan)
    render_swap_section()
    st.markdown("---")
    render_plan_actions()

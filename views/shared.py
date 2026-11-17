"""
State and actions shared by every page: the session's plan, saving it in the browser,
loading a saved plan, and sending feedback to the coach.
"""
import hashlib
import json

import streamlit as st

from services.planner import HealthForgePlanner
from services.plan_storage import serialize_plan, load_plan_file, PlanFileError
from services.plan_diff import describe_changes
from ui.browser_storage import read_item, write_item, remove_item
from ui.components import render_coach_reply, set_profile_form_values
from ui.scroll import scroll_to


def init_session_state() -> None:
    defaults = {
        "plan": None,
        "chat_history": [],
        "profile": None,
        "flash_message": None,
        "meal_log": [],
        "extracted_macros": None,
        "coach_reply": None,
        "loaded_plan_file_id": None,
        "browser_storage_checked": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_load_plan(label: str) -> None:
    """Uploader that restores a plan PDF or plan file downloaded from HealthForge."""
    uploaded = st.file_uploader(label, type=["pdf", "json"], key="plan_file_uploader")
    # The uploader keeps its file across reruns, so only load each file once.
    if uploaded is None or uploaded.file_id == st.session_state.loaded_plan_file_id:
        return

    st.session_state.loaded_plan_file_id = uploaded.file_id
    try:
        saved = load_plan_file(uploaded.getvalue())
    except PlanFileError as e:
        st.error(f"**Couldn't load that plan.** {e}", icon="🚨")
        return

    restore_plan(saved, "📂 Saved plan loaded.")


def restore_plan(saved: dict, message: str, open_plan: bool = True) -> None:
    """
    Makes a saved plan (from load_plan_file) the current one, then opens the plan page
    (or, with open_plan=False, redraws the page the visitor is on).
    """
    st.session_state.plan = saved["plan"]
    st.session_state.profile = saved["profile"]
    st.session_state.meal_log = saved["meal_log"]
    st.session_state.chat_history = saved["chat_history"]
    st.session_state.extracted_macros = None
    st.session_state.coach_reply = None
    set_profile_form_values(saved["profile"])
    st.session_state.flash_message = message
    if open_plan:
        go_to_plan()
    st.rerun()


def go_to_plan() -> None:
    """Opens the plan page (imported here to avoid a circular import with views.nav)."""
    from views.nav import plan_page
    st.switch_page(plan_page())


def start_over() -> None:
    """Clears the current plan; sync_browser_storage then forgets it on this device too."""
    st.session_state.plan = None
    st.session_state.profile = None
    st.session_state.meal_log = []
    st.session_state.chat_history = []
    st.session_state.extracted_macros = None
    st.session_state.coach_reply = None
    set_profile_form_values({})
    st.rerun()


BROWSER_STORAGE_NAME = "healthforge-plan"


def sync_browser_storage() -> None:
    """
    Keeps the current plan in the visitor's browser so it's still there when they come
    back on the same device. On a new visit, the stored plan is restored first; after
    that, every change to the plan is written back (or removed after Start Over).
    """
    if not st.session_state.browser_storage_checked:
        stored = read_item(BROWSER_STORAGE_NAME, key="browser_storage_read")
        if stored is None:
            return  # The browser answers on the next rerun
        st.session_state.browser_storage_checked = True
        # A plan made or uploaded before the browser answered takes priority.
        if stored and not st.session_state.plan:
            try:
                saved = load_plan_file(stored.encode("utf-8"))
            except PlanFileError:
                pass  # Unreadable (e.g. from an older version); it's replaced on next save
            else:
                # Stay on the page they opened (e.g. a bookmarked Coach page).
                restore_plan(saved, "👋 Welcome back! Your last plan was restored from this device.", open_plan=False)

    if not st.session_state.plan:
        remove_item(BROWSER_STORAGE_NAME, key="browser_storage_remove")
        return

    state = (
        st.session_state.profile,
        st.session_state.plan,
        st.session_state.meal_log,
        st.session_state.chat_history,
    )
    # serialize_plan stamps the current time, so detect changes from the content instead.
    digest = hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()[:16]
    write_item(BROWSER_STORAGE_NAME, serialize_plan(*state), key=f"browser_storage_write_{digest}")


def plan_key(plan: dict | None) -> str:
    """A short fingerprint of a plan's content, to tell whether it has changed since."""
    return hashlib.sha256(json.dumps(plan, sort_keys=True, default=str).encode()).hexdigest()[:16]


def apply_feedback(feedback: str, asked: str | None = None) -> None:
    """
    Sends feedback to the coach, records the exchange, and swaps in the updated plan.
    Keeps the coach's reply (its note and the list of what changed) to show the user.
    `asked` is how the request is shown to the user, if not the feedback text itself.
    """
    planner = HealthForgePlanner()
    old_plan = st.session_state.plan
    new_plan, note = planner.update_plan(
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
    st.session_state.coach_reply = {
        "asked": asked or feedback,
        "note": note,
        "changes": describe_changes(old_plan, new_plan),
        "plan_key": plan_key(new_plan),
        "fresh": True,
    }


def show_coach_reply() -> None:
    """
    Shows the coach's latest reply, until it's dismissed or the plan changes some other
    way (an edit, a swap, a new plan). A just-arrived reply pops in and is scrolled to.
    """
    reply = st.session_state.coach_reply
    if not reply or reply.get("plan_key") != plan_key(st.session_state.plan):
        return
    fresh = reply.get("fresh", False)
    key = render_coach_reply(reply, fresh=fresh)
    if fresh:
        scroll_to(key)
        reply["fresh"] = False

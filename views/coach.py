"""
The Coach page: tell the AI coach what to change, and see what it changed.
"""
import streamlit as st

from ui.alerts import show_error_alert
from views.shared import apply_feedback, show_coach_reply

_EXAMPLES = [
    "Deadlifts were too heavy",
    "Protect my sore shoulder",
    "I don't eat broccoli",
    "I only have 30 minutes on Fridays",
]


def coach_view() -> None:
    if not st.session_state.plan:
        from views.nav import profile_page
        st.info("You don't have a plan yet. Fill out your profile to get one.")
        st.page_link(profile_page(), label="Go to your profile", icon="👤")
        return

    st.subheader("💬 Talk to your coach")
    st.write(
        "Tell your coach what you'd like to change. It updates your plan and tells you "
        "exactly what it changed."
    )
    st.caption("Try something like:")
    st.markdown(
        '<div class="hf-chips">' + "".join(f'<span class="hf-chip">“{e}”</span>' for e in _EXAMPLES) + "</div>",
        unsafe_allow_html=True,
    )

    # Inside a column the box sits inline under this text. Pinned to the bottom of the
    # page (the default), it makes Streamlit keep scrolling to the bottom like a chat app.
    feedback = st.columns(1)[0].chat_input("What would you like to change?")
    if feedback:
        with st.spinner("Your coach is updating your plan..."):
            try:
                apply_feedback(feedback)
                st.rerun()
            except Exception as e:
                show_error_alert("update your plan with your feedback", e)

    show_coach_reply()

    earlier = [m["content"] for m in st.session_state.chat_history if m.get("role") == "user"]
    if earlier:
        with st.expander(f"Earlier requests ({len(earlier)})"):
            for request in reversed(earlier):
                st.markdown(f"- {request}")

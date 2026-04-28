import streamlit as st
import json

# Must be the very first Streamlit command
st.set_page_config(
    page_title="HealthForge AI",
    page_icon="💪",
    layout="wide",
)

from config import APP_NAME, APP_TAGLINE
from services.planner import HealthForgePlanner
from ui.components import render_header, render_user_profile_form, render_plan


def main() -> None:
    render_header(APP_NAME, APP_TAGLINE)

    with st.sidebar:
        st.markdown("### About")
        st.write(
            "HealthForge AI is a portfolio-grade fitness, nutrition, and habit coach "
            "powered by Llama 3.3 on Groq. It demonstrates end-to-end LLM integration, "
            "prompt engineering, and a Streamlit front end."
        )
        st.markdown("---")
        st.write("**Note:** This is not medical advice. Always consult a professional for health concerns.")

    profile, submitted = render_user_profile_form()

    # Initialize Session State
    if "plan" not in st.session_state:
        st.session_state.plan = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "profile" not in st.session_state:
        st.session_state.profile = None

    if submitted:
        with st.spinner("Generating your personalized plan with Llama 3.3 on Groq..."):
            try:
                planner = HealthForgePlanner()
                st.session_state.plan = planner.build_full_plan(profile)
                st.session_state.profile = profile
                st.session_state.chat_history = [] # Reset history on new plan
            except Exception as e:
                st.error(
                    "There was an error generating your plan. "
                    "Check your GROQ_API_KEY and console logs."
                )
                st.exception(e)
    elif not st.session_state.plan:
        st.info("Fill out your profile and click **Generate Plan** to get started.")

    if st.session_state.plan:
        render_plan(st.session_state.plan)
        
        st.markdown("---")
        st.subheader("Coach Feedback")
        st.write("Tell your AI Coach what you'd like to change (e.g., 'Deadlifts were too heavy', 'I don't eat broccoli').")
        
        feedback = st.chat_input("Enter your feedback here...")
        if feedback:
            with st.spinner("Updating your plan..."):
                try:
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
                    st.rerun()
                except Exception as e:
                    st.error("Error updating plan.")
                    st.exception(e)


if __name__ == "__main__":
    main()

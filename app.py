import streamlit as st

from config import APP_NAME, APP_TAGLINE
from services.planner import HealthForgePlanner
from ui.components import render_header, render_user_profile_form, render_plan


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="💪",
        layout="wide",
    )

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

    if submitted:
        with st.spinner("Generating your personalized plan with Llama 3.3 on Groq..."):
            try:
                planner = HealthForgePlanner()
                plan = planner.build_full_plan(profile)
                render_plan(plan)
            except Exception as e:
                st.error(
                    "There was an error generating your plan. "
                    "Check your GROQ_API_KEY and console logs."
                )
                st.exception(e)
    else:
        st.info("Fill out your profile and click **Generate Plan** to get started.")


if __name__ == "__main__":
    main()

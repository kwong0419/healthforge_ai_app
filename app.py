import streamlit as st

# Must be the very first Streamlit command
st.set_page_config(
    page_title="HealthForge AI",
    page_icon="💪",
    layout="wide",
)

from config import APP_NAME
from ui.scroll import scroll_to
from ui.styles import inject_styles
from views.nav import all_pages, render_nav_bar
from views.shared import init_session_state, sync_browser_storage


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### About")
        st.write(
            "HealthForge AI is a portfolio-grade fitness, nutrition, and habit coach "
            "powered by GPT-OSS on Groq. It demonstrates end-to-end LLM integration, "
            "prompt engineering, and a Streamlit front end."
        )
        st.markdown("---")
        st.write("**Note:** This is not medical advice. Always consult a professional for health concerns.")


def render_flash_message() -> None:
    """A one-time message about the last action (plan loaded, swapped, regenerated...)."""
    if not st.session_state.flash_message:
        return
    with st.container(key="flash_message"):
        st.success(st.session_state.flash_message)
    # The action was often lower down the page; bring its result into view.
    scroll_to("flash_message")
    st.session_state.flash_message = None


def main() -> None:
    inject_styles()
    init_session_state()
    render_sidebar()

    has_plan = bool(st.session_state.plan)
    pages = all_pages(has_plan)
    # Our own bar of links works the same on phones and desktop (the sidebar is hidden on phones).
    page = st.navigation(pages, position="hidden")

    if has_plan:
        st.markdown(f'<div class="hf-brand">💪 {APP_NAME}</div>', unsafe_allow_html=True)
        render_nav_bar(pages, page)
        render_flash_message()

    page.run()

    # Last, so it saves the plan as it is after the page has run.
    sync_browser_storage()


if __name__ == "__main__":
    main()

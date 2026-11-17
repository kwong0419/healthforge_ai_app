"""
The app's pages and the bar of links that moves between them. Every page is always
registered (so switch_page works), but the bar only shows once there's a plan.
"""
import streamlit as st

PLAN_PATH = "plan"
COACH_PATH = "coach"
MEALS_PATH = "meals"
PROFILE_PATH = "profile"


def plan_page(default: bool = False) -> st.Page:
    from views.plan import plan_view
    return st.Page(plan_view, title="My Plan", icon="💪", url_path=PLAN_PATH, default=default)


def coach_page() -> st.Page:
    from views.coach import coach_view
    return st.Page(coach_view, title="Coach", icon="💬", url_path=COACH_PATH)


def meals_page() -> st.Page:
    from views.meals import meals_view
    return st.Page(meals_view, title="Meals", icon="🍽️", url_path=MEALS_PATH)


def profile_page(default: bool = False) -> st.Page:
    from views.profile import profile_view
    return st.Page(profile_view, title="Profile", icon="👤", url_path=PROFILE_PATH, default=default)


def all_pages(has_plan: bool) -> list:
    """The plan page opens first once there's a plan; until then, the profile page."""
    return [
        plan_page(default=has_plan),
        coach_page(),
        meals_page(),
        profile_page(default=not has_plan),
    ]


# Short labels so all four fit in one row on a phone. Keyed by title, because the
# default page's url_path is empty.
_NAV = {"My Plan": ("Plan", "plan"), "Coach": ("Coach", "coach"), "Meals": ("Meals", "meals"), "Profile": ("Profile", "profile")}


def render_nav_bar(pages: list, current: st.Page) -> None:
    """A row of pill links to each page, with the current one highlighted."""
    with st.container(key="hf_inline_nav"):
        columns = st.columns(len(pages))
        for column, page in zip(columns, pages, strict=True):
            label, slug = _NAV.get(page.title, (page.title, "page"))
            active = "_active" if page.title == current.title else ""
            with column.container(key=f"hf_nav_{slug}{active}"):
                st.page_link(page, label=label, icon=page.icon)

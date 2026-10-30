import logging
from typing import Tuple

import groq
import streamlit as st

logger = logging.getLogger("healthforge")


def describe_error(error: Exception) -> Tuple[str, str]:
    """
    Translates an exception into a (what happened, what to do) pair for users.
    """
    if isinstance(error, groq.RateLimitError) or _groq_error_code(error) == "rate_limit_exceeded":
        return (
            "The AI coach is getting too many requests right now (free-tier limit).",
            "Wait about a minute, then try again.",
        )
    if isinstance(error, (groq.AuthenticationError, groq.PermissionDeniedError)):
        return (
            "The AI service rejected the app's API key.",
            "This needs to be fixed by the app owner. Please try again later.",
        )
    if isinstance(error, groq.NotFoundError):
        return (
            "The AI model this app uses is currently unavailable.",
            "This needs to be fixed by the app owner. Please try again later.",
        )
    if isinstance(error, groq.BadRequestError) and _groq_error_code(error) == "json_validate_failed":
        return (
            "The AI coach returned an incomplete response.",
            "This is usually a one-off. Please try again.",
        )
    if isinstance(error, (groq.APITimeoutError, groq.APIConnectionError)):
        return (
            "Couldn't reach the AI service.",
            "Check your internet connection and try again.",
        )
    if isinstance(error, groq.InternalServerError):
        return (
            "The AI service is having trouble right now.",
            "Please try again in a few minutes.",
        )
    if isinstance(error, ValueError) and str(error).startswith("The AI coach didn't suggest replacements"):
        return (
            "The AI coach couldn't find replacements for everything you picked.",
            "Please try again. Nothing in your plan was changed.",
        )
    if isinstance(error, ValueError) and "API_KEY is not set" in str(error):
        return (
            "The app isn't fully configured yet (missing API key).",
            "This needs to be fixed by the app owner.",
        )
    return (
        "Something unexpected went wrong.",
        "Please try again. If it keeps happening, the details below may help.",
    )


def show_error_alert(action: str, error: Exception) -> None:
    """
    Shows a friendly error alert for a failed action, with technical details
    tucked into an expander. The full traceback goes to the server logs.
    """
    logger.exception("Failed to %s", action)
    problem, next_step = describe_error(error)
    st.error(f"**Couldn't {action}.** {problem} {next_step}", icon="🚨")
    with st.expander("Technical details"):
        st.code(f"{type(error).__name__}: {error}", language=None)


def _groq_error_code(error: Exception) -> str | None:
    body = getattr(error, "body", None)
    if not isinstance(body, dict):
        return None
    inner = body.get("error", body)
    return inner.get("code") if isinstance(inner, dict) else None

from urllib.parse import quote_plus


def exercise_demo_url(name: str) -> str:
    """
    A YouTube search for form videos of an exercise. A search (rather than one fixed
    video) works for any exercise the AI suggests and never goes stale.
    """
    return f"https://www.youtube.com/results?search_query={quote_plus(f'{name} exercise proper form')}"

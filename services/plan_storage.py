import json
from datetime import datetime
from typing import Dict, Any, List

SAVE_FORMAT = "healthforge-plan"
SAVE_VERSION = 1


class PlanFileError(ValueError):
    """Raised when an uploaded plan file can't be loaded."""


def serialize_plan(
    profile: Dict[str, Any],
    plan: Dict[str, Any],
    meal_log: List[Dict[str, Any]],
    chat_history: List[Dict[str, str]],
) -> str:
    """
    Bundles everything needed to restore a session into a JSON string.
    """
    payload = {
        "format": SAVE_FORMAT,
        "version": SAVE_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "profile": profile,
        "plan": plan,
        "meal_log": meal_log,
        "chat_history": chat_history,
    }
    return json.dumps(payload, indent=2)


def deserialize_plan(raw: bytes) -> Dict[str, Any]:
    """
    Parses and validates a saved plan file. Raises PlanFileError with a
    user-friendly message if the file isn't a HealthForge plan.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PlanFileError("That file isn't valid JSON.")

    if not isinstance(data, dict) or data.get("format") != SAVE_FORMAT:
        raise PlanFileError("That file isn't a HealthForge plan.")
    if data.get("version", 0) > SAVE_VERSION:
        raise PlanFileError("That plan was saved by a newer version of HealthForge.")
    if not isinstance(data.get("plan"), dict) or not isinstance(data.get("profile"), dict):
        raise PlanFileError("That plan file is missing its plan or profile.")

    return {
        "profile": data["profile"],
        "plan": data["plan"],
        "meal_log": data.get("meal_log") or [],
        "chat_history": data.get("chat_history") or [],
    }

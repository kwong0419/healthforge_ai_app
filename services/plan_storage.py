import io
import json
from datetime import datetime
from typing import Dict, Any, List

from pypdf import PdfReader

SAVE_FORMAT = "healthforge-plan"
SAVE_VERSION = 1

# Name of the plan data file attached inside downloaded PDFs.
PDF_ATTACHMENT_NAME = "healthforge-plan.json"


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


def load_plan_file(raw: bytes) -> Dict[str, Any]:
    """
    Loads a plan from an uploaded file: either a saved plan file (JSON) or a PDF
    downloaded from HealthForge, which carries the same data as an attachment.
    """
    if raw[:5] == b"%PDF-":
        return deserialize_plan(_extract_plan_from_pdf(raw))
    return deserialize_plan(raw)


def _extract_plan_from_pdf(raw: bytes) -> bytes:
    try:
        attachments = PdfReader(io.BytesIO(raw)).attachments
    except Exception:
        raise PlanFileError("That PDF couldn't be read.") from None

    data = attachments.get(PDF_ATTACHMENT_NAME)
    if not data:
        raise PlanFileError(
            "That PDF doesn't contain HealthForge plan data. PDFs downloaded before this "
            "feature was added can't be reloaded — download a fresh PDF of your plan."
        )
    return data[0]


def deserialize_plan(raw: bytes) -> Dict[str, Any]:
    """
    Parses and validates a saved plan file. Raises PlanFileError with a
    user-friendly message if the file isn't a HealthForge plan.
    """
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PlanFileError("That file isn't valid JSON.") from None

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

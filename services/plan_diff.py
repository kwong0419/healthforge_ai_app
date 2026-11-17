"""
Works out what changed between two versions of a plan, so the user can see exactly
what the coach did with their feedback. This compares the plans directly rather than
asking the AI, so the list is always accurate.
"""
from typing import Any, Dict, List, Tuple

from services.planner import AUDIT_WARNING_MARKER

# A section title and its lines, e.g. ("Mon · Upper Body", ["Removed Overhead Press"]).
Changes = List[Tuple[str, List[str]]]

_NOTE_PREVIEW = 140


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _short(text: str, limit: int = _NOTE_PREVIEW) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _dose(exercise: Dict[str, Any]) -> str:
    sets, reps = _text(exercise.get("sets")), _text(exercise.get("reps"))
    if sets and reps:
        return f"{sets} × {reps}"
    return sets or reps


def _name(item: Dict[str, Any], field: str) -> str:
    return _text(item.get(field)) or "Unnamed"


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _section(plan: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = plan.get(key)
    return value if isinstance(value, dict) else {}


def _dicts(value: Any) -> List[Dict[str, Any]]:
    return [v for v in _list(value) if isinstance(v, dict)]


def _strings(value: Any) -> List[str]:
    return [_text(v) for v in _list(value) if _text(v)]


def _day_changes(old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
    lines = []
    if _text(old.get("focus")) != _text(new.get("focus")) and _text(new.get("focus")):
        lines.append(f"Focus is now: {_text(new.get('focus'))}")

    old_ex, new_ex = _dicts(old.get("exercises")), _dicts(new.get("exercises"))
    old_by_name = {_name(e, "name").lower(): e for e in old_ex}
    new_by_name = {_name(e, "name").lower(): e for e in new_ex}
    removed = [e for e in old_ex if _name(e, "name").lower() not in new_by_name]
    added = [e for e in new_ex if _name(e, "name").lower() not in old_by_name]

    # A removal and an addition together usually means one exercise replaced another.
    for gone, came in zip(removed, added, strict=False):
        line = f"Replaced {_name(gone, 'name')} with {_name(came, 'name')}"
        if _dose(came):
            line += f" ({_dose(came)})"
        lines.append(line)
    for gone in removed[len(added):]:
        lines.append(f"Removed {_name(gone, 'name')}")
    for came in added[len(removed):]:
        line = f"Added {_name(came, 'name')}"
        if _dose(came):
            line += f" ({_dose(came)})"
        lines.append(line)

    for exercise in new_ex:
        before = old_by_name.get(_name(exercise, "name").lower())
        if before is None:
            continue
        name = _name(exercise, "name")
        if _dose(before) != _dose(exercise):
            lines.append(f"{name}: {_dose(before) or 'no sets'} → {_dose(exercise) or 'no sets'}")
        new_notes = _text(exercise.get("notes"))
        if new_notes and new_notes != _text(before.get("notes")):
            lines.append(f"{name}: new notes — “{_short(new_notes)}”")
    return lines


def _workout_changes(old: Dict[str, Any], new: Dict[str, Any]) -> Changes:
    sections: Changes = []
    old_days = _dicts(_section(old, "workout_plan").get("weekly_split"))
    new_days = _dicts(_section(new, "workout_plan").get("weekly_split"))
    for i in range(max(len(old_days), len(new_days))):
        if i >= len(new_days):
            sections.append((_name(old_days[i], "day"), ["This day was removed"]))
        elif i >= len(old_days):
            names = ", ".join(_name(e, "name") for e in _dicts(new_days[i].get("exercises")))
            sections.append((_name(new_days[i], "day"), [f"New day added: {names}" if names else "New day added"]))
        else:
            lines = _day_changes(old_days[i], new_days[i])
            if lines:
                sections.append((_name(new_days[i], "day"), lines))

    old_prog = _text(_section(old, "workout_plan").get("progression_notes"))
    new_prog = _text(_section(new, "workout_plan").get("progression_notes"))
    if new_prog and new_prog != old_prog:
        sections.append(("Progression", [f"Updated — “{_short(new_prog)}”"]))
    return sections


def _nutrition_changes(old: Dict[str, Any], new: Dict[str, Any]) -> Changes:
    old_n, new_n = _section(old, "nutrition_plan"), _section(new, "nutrition_plan")
    lines = []
    if _text(new_n.get("philosophy")) and _text(new_n.get("philosophy")) != _text(old_n.get("philosophy")):
        lines.append(f"New approach — “{_short(_text(new_n.get('philosophy')))}”")

    old_meals, new_meals = _dicts(old_n.get("daily_structure")), _dicts(new_n.get("daily_structure"))
    for i in range(max(len(old_meals), len(new_meals))):
        if i >= len(new_meals):
            lines.append(f"Removed {_name(old_meals[i], 'meal')}: {_text(old_meals[i].get('example'))}")
        elif i >= len(old_meals):
            lines.append(f"Added {_name(new_meals[i], 'meal')}: {_text(new_meals[i].get('example'))}")
        elif _text(old_meals[i].get("example")) != _text(new_meals[i].get("example")):
            lines.append(f"{_name(new_meals[i], 'meal')}: now {_text(new_meals[i].get('example'))}")

    old_groceries = {g.lower() for g in _strings(old_n.get("grocery_list"))}
    new_groceries = _strings(new_n.get("grocery_list"))
    new_lower = {g.lower() for g in new_groceries}
    added = [g for g in new_groceries if g.lower() not in old_groceries]
    removed = [g for g in _strings(old_n.get("grocery_list")) if g.lower() not in new_lower]
    if added:
        lines.append("Groceries added: " + ", ".join(added))
    if removed:
        lines.append("Groceries removed: " + ", ".join(removed))
    return [("Nutrition", lines)] if lines else []


def _habit_changes(old: Dict[str, Any], new: Dict[str, Any]) -> Changes:
    old_h, new_h = _section(old, "habits_and_lifestyle"), _section(new, "habits_and_lifestyle")
    lines = []
    for key in new_h:
        before = set(_strings(old_h.get(key)))
        topic = key.replace("_", " ").capitalize()
        for tip in _strings(new_h.get(key)):
            if tip not in before:
                lines.append(f"{topic}: {_short(tip)}")
    return [("Habits", lines)] if lines else []


def _disclaimer_changes(old: Dict[str, Any], new: Dict[str, Any]) -> Changes:
    before = set(_strings(old.get("disclaimers")))
    lines = [
        _short(d) for d in _strings(new.get("disclaimers"))
        if d not in before and AUDIT_WARNING_MARKER not in d
    ]
    return [("Safety notes", lines)] if lines else []


def describe_changes(old: Dict[str, Any], new: Dict[str, Any]) -> Changes:
    """
    Lists what changed from the old plan to the new one, grouped by section (each
    workout day, then nutrition, habits and safety notes). Empty if nothing did.
    """
    old = old if isinstance(old, dict) else {}
    new = new if isinstance(new, dict) else {}
    return (
        _workout_changes(old, new)
        + _nutrition_changes(old, new)
        + _habit_changes(old, new)
        + _disclaimer_changes(old, new)
    )

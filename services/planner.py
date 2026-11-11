import copy
from typing import Dict, Any, List, Tuple
from services.llm_client import HealthForgeLLMClient

AUDIT_WARNING_MARKER = "did not pass the automated AI safety audit"


def failed_safety_audit(plan: Dict[str, Any]) -> bool:
    return any(AUDIT_WARNING_MARKER in d for d in plan.get("disclaimers", []) if isinstance(d, str))


def _set_audit_warning(plan: Dict[str, Any], reason: str | None) -> Dict[str, Any]:
    """
    Removes any audit warning carried over from an earlier version (the LLM sees and
    may copy old disclaimers), then adds a fresh one if this version failed.
    """
    disclaimers = [d for d in plan.get("disclaimers", []) if not (isinstance(d, str) and AUDIT_WARNING_MARKER in d)]
    if reason is not None:
        disclaimers.append(
            f"⚠️ WARNING: This plan {AUDIT_WARNING_MARKER}. Please review carefully. "
            f"Auditor's last concern: {reason}"
        )
    plan["disclaimers"] = disclaimers
    return plan


class HealthForgePlanner:
    """
    High-level orchestrator that uses the LLM client to build plans.
    """

    def __init__(self) -> None:
        self.llm_client = HealthForgeLLMClient()

    def build_full_plan(self, user_profile: Dict[str, Any], max_retries: int = 2) -> Dict[str, Any]:
        """
        Main entry point: given a user profile, return a structured plan.
        Includes a Safety Audit loop to auto-fix unsafe plans up to max_retries.
        """
        plan = self.llm_client.generate_plan(user_profile)

        for attempt in range(max_retries):
            audit_result = self.llm_client.audit_plan(user_profile, plan)
            if audit_result.get("status") == "PASSED":
                return _set_audit_warning(plan, reason=None)
            
            # The plan failed the audit. Attempt to auto-fix it.
            reason = audit_result.get("reason", "Safety audit failed.")
            auto_feedback = f"The safety auditor rejected the plan for this reason: {reason}. Please fix the plan to address these safety concerns."
            
            # Use update_plan to refine the current plan based on the auditor's feedback
            plan = self.llm_client.update_plan(user_profile, plan, [], auto_feedback)
            
        # If we exhausted retries, append a safety warning and return the plan as-is
        return _set_audit_warning(plan, reason)

    def update_plan(self, user_profile: Dict[str, Any], current_plan: Dict[str, Any], chat_history: list, new_feedback: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Update an existing plan based on feedback.
        Includes a Safety Audit loop to auto-fix unsafe plan updates up to max_retries.
        """
        plan = self.llm_client.update_plan(user_profile, current_plan, chat_history, new_feedback)

        for attempt in range(max_retries):
            audit_result = self.llm_client.audit_plan(user_profile, plan)
            if audit_result.get("status") == "PASSED":
                return _set_audit_warning(plan, reason=None)
                
            # The updated plan failed the audit. Attempt to auto-fix it.
            reason = audit_result.get("reason", "Safety audit failed.")
            auto_feedback = f"The safety auditor rejected the updated plan for this reason: {reason}. Please fix the plan to address these safety concerns."
            
            # We don't append auto-feedback to the visible chat_history, just use it to correct the current iteration
            plan = self.llm_client.update_plan(user_profile, plan, chat_history, auto_feedback)
            
        # If we exhausted retries, append a safety warning
        return _set_audit_warning(plan, reason)

    def find_swap_options(
        self,
        user_profile: Dict[str, Any],
        plan: Dict[str, Any],
        exercise_ids: List[str],
        meal_ids: List[str],
        preferences: str = "",
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Gets a few replacement choices for each chosen exercise ("d<day>e<exercise>") and
        meal ("m<meal>"), steered by the user's optional preferences. Returns {id: [options]}.
        """
        options = {}
        if exercise_ids:
            options.update(self.llm_client.suggest_exercise_options(user_profile, plan, exercise_ids, preferences))
        if meal_ids:
            options.update(self.llm_client.suggest_meal_options(user_profile, plan, meal_ids, preferences))
        missing = [i for i in exercise_ids + meal_ids if i not in options]
        if missing:
            raise ValueError(f"The AI coach didn't suggest replacements for: {', '.join(missing)}")
        return options

    def apply_swap_choices(
        self, user_profile: Dict[str, Any], plan: Dict[str, Any], choices: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
        """
        Puts the options the user picked ({id: option}) into a copy of the plan, then runs the
        Safety Audit once. The user's picks are kept either way; a failed audit adds the usual
        warning. Returns the new plan and a list of (old, new) pairs.
        """
        exercises = {i: c for i, c in choices.items() if i.startswith("d")}
        meals = {i: c for i, c in choices.items() if i.startswith("m")}
        grocery_additions = [item for c in meals.values() for item in c.get("grocery_additions", [])]

        new_plan, changes = _apply_swaps(plan, exercises)
        changes += _apply_meal_swaps(
            new_plan, {i: {k: c.get(k, "") for k in ("example", "notes")} for i, c in meals.items()}, grocery_additions
        )
        return self.safety_check(user_profile, new_plan), changes

    def safety_check(self, user_profile: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the Safety Audit on a plan as it stands (e.g. after the user's own edits) and
        sets or clears its audit warning. Updates and returns the plan it was given.
        """
        audit_result = self.llm_client.audit_plan(user_profile, plan)
        if audit_result.get("status") == "PASSED":
            return _set_audit_warning(plan, reason=None)
        return _set_audit_warning(plan, audit_result.get("reason", "Safety audit failed."))


def _apply_swaps(
    plan: Dict[str, Any], replacements: Dict[str, Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    new_plan = copy.deepcopy(plan)
    changes = []
    for d, day in enumerate(new_plan.get("workout_plan", {}).get("weekly_split", [])):
        exercises = day.get("exercises", [])
        for e, old in enumerate(exercises):
            new = replacements.get(f"d{d}e{e}")
            if new:
                old_name = old.get("name", "Exercise") if isinstance(old, dict) else str(old)
                changes.append((old_name, new["name"]))
                exercises[e] = new
    return new_plan, changes



def _apply_meal_swaps(
    plan: Dict[str, Any], replacements: Dict[str, Dict[str, Any]], grocery_additions: List[str]
) -> List[Tuple[str, str]]:
    """Merges meal replacements and new grocery items into plan (already a copy)."""
    nutrition = plan.setdefault("nutrition_plan", {})
    meals = nutrition.get("daily_structure", [])
    changes = []
    for m, old in enumerate(meals):
        new = replacements.get(f"m{m}")
        if new:
            slot = old.get("meal", "Meal") if isinstance(old, dict) else "Meal"
            meals[m] = {**new, "meal": slot}  # The slot (e.g. Breakfast) never changes
            changes.append((slot, new["example"]))

    grocery = nutrition.setdefault("grocery_list", [])
    have = {str(item).strip().lower() for item in grocery}
    for item in grocery_additions:
        if item.strip().lower() not in have:
            grocery.append(item)
            have.add(item.strip().lower())
    return changes

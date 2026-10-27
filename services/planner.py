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

    def swap_exercises(
        self, user_profile: Dict[str, Any], plan: Dict[str, Any], swap_ids: List[str], max_retries: int = 2
    ) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
        """
        Replaces only the chosen exercises ("d<day>e<exercise>" ids); every other part of
        the plan is kept exactly as it was. Includes the same Safety Audit loop as other
        updates. Returns the new plan and a list of (old name, new name) pairs.
        """
        extra_instructions = ""
        reason = None
        for attempt in range(max_retries + 1):
            replacements = self.llm_client.suggest_exercise_swaps(user_profile, plan, swap_ids, extra_instructions)
            missing = [i for i in swap_ids if i not in replacements]
            if missing:
                raise ValueError(f"The AI coach didn't suggest replacements for: {', '.join(missing)}")

            new_plan, changes = _apply_swaps(plan, replacements)
            if attempt == max_retries:
                break

            audit_result = self.llm_client.audit_plan(user_profile, new_plan)
            if audit_result.get("status") == "PASSED":
                return _set_audit_warning(new_plan, reason=None), changes

            reason = audit_result.get("reason", "Safety audit failed.")
            extra_instructions = (
                f"A safety auditor rejected your previous choices ({', '.join(new for _, new in changes)}) "
                f"for this reason: {reason}. Choose safer replacements."
            )

        return _set_audit_warning(new_plan, reason), changes


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


from typing import Dict, Any
from services.llm_client import HealthForgeLLMClient


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
                return plan
            
            # The plan failed the audit. Attempt to auto-fix it.
            reason = audit_result.get("reason", "Safety audit failed.")
            auto_feedback = f"The safety auditor rejected the plan for this reason: {reason}. Please fix the plan to address these safety concerns."
            
            # Use update_plan to refine the current plan based on the auditor's feedback
            plan = self.llm_client.update_plan(user_profile, plan, [], auto_feedback)
            
        # If we exhausted retries, append a safety warning and return the plan as-is
        plan.setdefault("disclaimers", []).append("⚠️ WARNING: This plan did not pass the automated AI safety audit. Please review carefully.")
        return plan

    def update_plan(self, user_profile: Dict[str, Any], current_plan: Dict[str, Any], chat_history: list, new_feedback: str, max_retries: int = 2) -> Dict[str, Any]:
        """
        Update an existing plan based on feedback.
        Includes a Safety Audit loop to auto-fix unsafe plan updates up to max_retries.
        """
        plan = self.llm_client.update_plan(user_profile, current_plan, chat_history, new_feedback)

        for attempt in range(max_retries):
            audit_result = self.llm_client.audit_plan(user_profile, plan)
            if audit_result.get("status") == "PASSED":
                return plan
                
            # The updated plan failed the audit. Attempt to auto-fix it.
            reason = audit_result.get("reason", "Safety audit failed.")
            auto_feedback = f"The safety auditor rejected the updated plan for this reason: {reason}. Please fix the plan to address these safety concerns."
            
            # We don't append auto-feedback to the visible chat_history, just use it to correct the current iteration
            plan = self.llm_client.update_plan(user_profile, plan, chat_history, auto_feedback)
            
        # If we exhausted retries, append a safety warning
        plan.setdefault("disclaimers", []).append("⚠️ WARNING: This updated plan did not pass the automated AI safety audit. Please review carefully.")
        return plan

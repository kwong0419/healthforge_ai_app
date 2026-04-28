from typing import Dict, Any
from services.llm_client import HealthForgeLLMClient


class HealthForgePlanner:
    """
    High-level orchestrator that uses the LLM client to build plans.
    """

    def __init__(self) -> None:
        self.llm_client = HealthForgeLLMClient()

    def build_full_plan(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point: given a user profile, return a structured plan.
        """
        return self.llm_client.generate_plan(user_profile)

    def update_plan(self, user_profile: Dict[str, Any], current_plan: Dict[str, Any], chat_history: list, new_feedback: str) -> Dict[str, Any]:
        """
        Update an existing plan based on feedback.
        """
        return self.llm_client.update_plan(user_profile, current_plan, chat_history, new_feedback)

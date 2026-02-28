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

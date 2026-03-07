from typing import Dict, Any
import json

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL_NAME
from prompts.system_prompt import SYSTEM_PROMPT


class HealthForgeLLMClient:
    """
    Thin wrapper around Groq's LLM client using Llama 3.3 Versatile.
    """

    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Please set it in your environment.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate_plan(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls the LLM with a structured user profile and expects JSON back.
        """
        user_prompt = self._build_user_prompt(user_profile)

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=2048,
        )

        content = response.choices[0].message.content

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: wrap raw content in a safe JSON structure
            parsed = {
                "summary": "There was an issue parsing the structured response. Showing raw content.",
                "workout_plan": {"weekly_split": [], "progression_notes": ""},
                "nutrition_plan": {
                    "philosophy": "",
                    "daily_structure": [],
                    "grocery_list": [],
                },
                "habits_and_lifestyle": {
                    "sleep": [],
                    "stress_management": [],
                    "daily_habits": [],
                },
                "disclaimers": [content],
            }

        return parsed

    def _build_user_prompt(self, profile: Dict[str, Any]) -> str:
        """
        Convert the user profile dict into a natural language + structured description.
        """
        return f"""
User profile for personalized fitness, nutrition, and habit plan:

- Name (optional): {profile.get("name") or "N/A"}
- Age range: {profile.get("age_range")}
- Gender (if provided): {profile.get("gender")}
- Training experience: {profile.get("experience_level")}
- Primary goal: {profile.get("primary_goal")}
- Secondary goal: {profile.get("secondary_goal")}
- Workout frequency (days/week): {profile.get("days_per_week")}
- Session length: {profile.get("session_length")}
- Equipment available: {profile.get("equipment")}
- Injuries / limitations (non-medical description): {profile.get("limitations")}
- Dietary preference: {profile.get("diet_preference")}
- Dietary restrictions: {profile.get("diet_restrictions")}
- Typical schedule / constraints: {profile.get("schedule")}
- Additional notes: {profile.get("notes")}

Please generate a safe, evidence-based plan in the required JSON format.
"""

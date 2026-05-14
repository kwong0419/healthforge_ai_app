from typing import Dict, Any
import json
import re

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL_NAME
from prompts.system_prompt import SYSTEM_PROMPT
from prompts.auditor_prompt import AUDITOR_PROMPT


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
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        cleaned = self._clean_json_response(content)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: wrap raw content in a safe JSON structure
            parsed = self._fallback_parse(content)

        return parsed

    def update_plan(self, profile: Dict[str, Any], current_plan: Dict[str, Any], chat_history: list, new_feedback: str) -> Dict[str, Any]:
        """
        Updates an existing plan using conversation history and new user feedback.
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # First user message is the profile context
        messages.append({"role": "user", "content": self._build_user_prompt(profile)})
        
        # Append the chat history (if any)
        for msg in chat_history:
            messages.append(msg)
            
        # Append the current plan so the LLM knows what to modify
        messages.append({"role": "assistant", "content": json.dumps(current_plan)})
        
        # Append the new feedback
        messages.append({"role": "user", "content": new_feedback})

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=messages,
            temperature=0.4,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        cleaned = self._clean_json_response(content)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = self._fallback_parse(content)

        return parsed

    def audit_plan(self, profile: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, str]:
        """
        Sends the generated plan to the Safety Auditor for a peer review.
        Returns a dict with 'status' (PASSED/FAILED) and 'reason'.
        """
        # We need the profile so the auditor knows the user's constraints (e.g. allergies, time limit)
        user_context = self._build_user_prompt(profile)
        
        # We provide the generated plan for review
        plan_json = json.dumps(plan, indent=2)
        
        audit_content = f"{user_context}\n\nHere is the generated plan to review:\n{plan_json}"

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": AUDITOR_PROMPT},
                {"role": "user", "content": audit_content},
            ],
            temperature=0.2, # Lower temperature for a stricter, more deterministic audit
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        cleaned = self._clean_json_response(content)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # If the auditor itself fails to return valid JSON, assume it failed for safety
            parsed = {
                "status": "FAILED",
                "reason": "Auditor failed to return a valid JSON response. Please ensure the plan is strictly safe and formatted correctly."
            }

        return parsed

    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        return {
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

    @staticmethod
    def _clean_json_response(content: str) -> str:
        """
        Strip markdown code fences (```json ... ```) that LLMs often wrap around JSON.
        """
        content = content.strip()
        # Remove ```json ... ``` or ``` ... ``` wrapping
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        return content.strip()

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

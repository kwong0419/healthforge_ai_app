from typing import Dict, Any, List
import json
import re

from groq import Groq, BadRequestError
from config import GROQ_API_KEY, LLM_MODEL_NAME
from prompts.system_prompt import SYSTEM_PROMPT
from prompts.auditor_prompt import AUDITOR_PROMPT
from prompts.swap_prompt import SWAP_PROMPT

# GPT-OSS is a reasoning model: its hidden reasoning counts toward max_tokens, and if
# the budget runs out mid-reasoning Groq returns an empty answer and rejects it as
# invalid JSON. Groq's free tier also rejects any request whose prompt + max_tokens
# exceeds 8,000 tokens, so each budget is sized to fit under that with its prompt.
GENERATE_MAX_TOKENS = 5000  # ~900 prompt + ~2,800 plan
UPDATE_MAX_TOKENS = 4000    # ~3,700 prompt (includes current plan) + ~2,800 plan
AUDIT_MAX_TOKENS = 3000     # ~3,500 prompt (includes plan) + ~1,000 reasoning/verdict
SWAP_MAX_TOKENS = 3000      # ~1,500 prompt (exercise names only) + reasoning + a few exercises

# Writing the plan JSON needs little reasoning; the auditor keeps the default effort.
PLAN_REASONING_EFFORT = "low"


class HealthForgeLLMClient:
    """
    Thin wrapper around Groq's LLM client (model set in config.LLM_MODEL_NAME).
    """

    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Please set it in your environment.")
        # Extra retries let multi-call flows (generate -> audit -> fix) wait out
        # per-minute rate limits instead of failing.
        self.client = Groq(api_key=GROQ_API_KEY, max_retries=5)

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
            max_tokens=GENERATE_MAX_TOKENS,
            reasoning_effort=PLAN_REASONING_EFFORT,
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
        
        # Append past feedback only. Earlier plan versions are skipped: the current plan
        # is sent below, and each old copy would add ~2,700 tokens to the request.
        for msg in chat_history:
            if msg.get("role") == "user":
                messages.append(msg)
            
        # Append the current plan so the LLM knows what to modify
        messages.append({"role": "assistant", "content": json.dumps(current_plan)})
        
        # Append the new feedback
        messages.append({"role": "user", "content": new_feedback})

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=messages,
            temperature=0.4,
            max_tokens=UPDATE_MAX_TOKENS,
            reasoning_effort=PLAN_REASONING_EFFORT,
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
        plan_json = json.dumps(plan)  # Compact to save tokens
        
        audit_content = f"{user_context}\n\nHere is the generated plan to review:\n{plan_json}"

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": AUDITOR_PROMPT},
                    {"role": "user", "content": audit_content},
                ],
                temperature=0.2, # Lower temperature for a stricter, more deterministic audit
                max_tokens=AUDIT_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = json.loads(self._clean_json_response(content))
        except BadRequestError as e:
            # Groq rejects output that isn't valid JSON; treat it like a parse failure below
            error = (e.body or {}).get("error", {}) if isinstance(e.body, dict) else {}
            if error.get("code") != "json_validate_failed":
                raise
            parsed = None
        except json.JSONDecodeError:
            parsed = None

        if parsed is None:
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

    def suggest_exercise_swaps(
        self,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        swap_ids: List[str],
        extra_instructions: str = "",
    ) -> Dict[str, Dict[str, Any]]:
        """
        Asks for replacements for specific exercises only, identified as "d<day>e<exercise>"
        (e.g. "d0e2" is the third exercise on the first day). Returns {id: new exercise}.
        Only exercise names are sent for context, so this stays small and fast.
        """
        overview = []
        for d, day in enumerate(plan.get("workout_plan", {}).get("weekly_split", [])):
            overview.append(f"{day.get('day', f'Day {d + 1}')} (focus: {day.get('focus', 'n/a')})")
            for e, ex in enumerate(day.get("exercises", [])):
                ex_id = f"d{d}e{e}"
                marker = "  <-- REPLACE" if ex_id in swap_ids else ""
                details = f"{ex.get('name')} - {ex.get('sets')} x {ex.get('reps')}" if isinstance(ex, dict) else str(ex)
                overview.append(f"  [{ex_id}] {details}{marker}")

        content = (
            f"{self._profile_summary(profile)}\n"
            "Current workout plan:\n" + "\n".join(overview) + "\n\n"
            f"Replace exactly these exercises: {', '.join(swap_ids)}."
        )
        if extra_instructions:
            content += f"\n\n{extra_instructions}"

        response = self.client.chat.completions.create(
            model=LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": SWAP_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.6,  # Higher than plan writing, so swaps feel genuinely new
            max_tokens=SWAP_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        parsed = json.loads(self._clean_json_response(response.choices[0].message.content))
        return {
            r["id"]: {key: r.get(key, "") for key in ("name", "sets", "reps", "notes")}
            for r in parsed.get("replacements", [])
            if isinstance(r, dict) and r.get("id") in swap_ids and r.get("name")
        }

    def _build_user_prompt(self, profile: Dict[str, Any]) -> str:
        """
        Convert the user profile dict into a natural language + structured description.
        """
        return f"""{self._profile_summary(profile)}
Please generate a safe, evidence-based plan in the required JSON format.
"""

    @staticmethod
    def _profile_summary(profile: Dict[str, Any]) -> str:
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
"""

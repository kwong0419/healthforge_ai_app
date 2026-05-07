"""
Gemini Vision Service for extracting nutrition data from food images.
Uses Google's Gemini 2.5 Flash model (free tier via AI Studio).
"""

import base64
import json
import time
from typing import Dict, Any
import requests


class GeminiVisionClient:
    """
    Extracts macronutrient data from food images using Gemini Vision API.
    Supports both food labels and plate photos.
    """

    # Gemini API endpoint (using AI Studio free tier)
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

    # Retry settings for rate-limit handling
    MAX_RETRIES = 3

    def __init__(self, api_key: str) -> None:
        """Initialize with Gemini API key from config."""
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please set it in your environment.")
        self.api_key = api_key

    def extract_macros_from_image(self, image_data: bytes, image_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Sends an image to Gemini and extracts macronutrient data.
        
        Args:
            image_data: Binary image data (bytes)
            image_type: MIME type of image (e.g., "image/jpeg", "image/png")
            
        Returns:
            Dict with keys: protein_g, carbs_g, fat_g, calories, food_description, confidence
        """
        # Encode image to base64
        base64_image = base64.standard_b64encode(image_data).decode("utf-8")

        # Build the prompt for Gemini
        extraction_prompt = """Analyze this image of food and extract nutritional information.

Return ONLY a JSON object with these fields (estimate if exact values not visible):
{
    "food_description": "Brief description of the food/meal",
    "portion_size": "Estimated portion (e.g., '1 breast', '1 cup', 'whole plate')",
    "protein_g": <number>,
    "carbs_g": <number>,
    "fat_g": <number>,
    "calories": <number>,
    "confidence": "<high|medium|low>",
    "notes": "Any relevant notes (e.g., 'estimate based on portion size', 'label text visible')"
}

Be conservative in estimates. If you cannot identify the food, return confidence: "low"."""

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": image_type,
                                "data": base64_image,
                            }
                        },
                        {
                            "text": extraction_prompt
                        }
                    ]
                }
            ]
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                # Pass the API key via params dict so it never appears in
                # formatted URL strings or exception messages.
                response = requests.post(
                    self.GEMINI_API_URL,
                    params={"key": self.api_key},
                    json=payload,
                    timeout=30
                )

                # Handle rate-limit with exponential backoff before raising
                if response.status_code == 429:
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)  # 1s -> 2s -> 4s
                        continue
                    return self._error_response(
                        "Rate limit reached. The free tier allows a limited number of "
                        "requests per minute — please wait a moment and try again."
                    )

                response.raise_for_status()

                result = response.json()
                
                # Extract text from Gemini response
                if "candidates" not in result or not result["candidates"]:
                    return self._error_response("No response from Gemini")

                candidate = result["candidates"][0]
                if "content" not in candidate or "parts" not in candidate["content"]:
                    return self._error_response("Invalid Gemini response structure")

                text_content = candidate["content"]["parts"][0].get("text", "")
                
                # Parse JSON from response
                parsed = self._parse_json_response(text_content)
                return parsed

            except requests.exceptions.RequestException as e:
                # Scrub API key from the exception message before surfacing it
                safe_msg = str(e).replace(self.api_key, "***")
                return self._error_response(f"API request failed: {safe_msg}")
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                return self._error_response(f"Failed to parse Gemini response: {str(e)}")

        return self._error_response("Max retries exceeded. Please try again shortly.")

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract and parse JSON from Gemini response."""
        try:
            # Try to find JSON block in response
            start = text.find("{")
            end = text.rfind("}") + 1
            
            if start == -1 or end == 0:
                return self._error_response("No JSON found in response")
            
            json_str = text[start:end]
            parsed = json.loads(json_str)
            
            # Validate required fields
            required = ["protein_g", "carbs_g", "fat_g", "calories", "food_description"]
            if not all(k in parsed for k in required):
                return self._error_response("Missing required fields in response")
            
            # Ensure numeric values
            parsed["protein_g"] = float(parsed.get("protein_g", 0))
            parsed["carbs_g"] = float(parsed.get("carbs_g", 0))
            parsed["fat_g"] = float(parsed.get("fat_g", 0))
            parsed["calories"] = float(parsed.get("calories", 0))
            
            return parsed

        except json.JSONDecodeError:
            return self._error_response("Failed to parse JSON from response")

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Return a safe error response structure."""
        return {
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "calories": 0,
            "food_description": "Unable to analyze",
            "confidence": "low",
            "error": error_msg
        }

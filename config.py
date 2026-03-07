import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Groq model name – see https://console.groq.com/docs/models for options
LLM_MODEL_NAME = "llama-3.3-70b-versatile"

APP_NAME = "HealthForge AI"
APP_TAGLINE = "Evidence-based fitness, nutrition, and habit coaching powered by Llama 3.3 on Groq."

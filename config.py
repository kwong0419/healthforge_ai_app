import os
from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY", "")

# Grok model name – adjust if Grok changes naming
LLM_MODEL_NAME = "llama-3.3-70b-versatile"

APP_NAME = "HealthForge AI"
APP_TAGLINE = "Evidence-based fitness, nutrition, and habit coaching powered by Llama 3.3 on Grok."

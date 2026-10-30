import os
from dotenv import load_dotenv

load_dotenv()

# On Streamlit Cloud, secrets live in st.secrets, not os.environ.
# Fall back to os.getenv for local development via .env file.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GROQ_API_KEY:
    try:
        import streamlit as st
        GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")
        GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", GEMINI_API_KEY)
    except Exception:
        pass

# Groq model name – see https://console.groq.com/docs/models for options
LLM_MODEL_NAME = "openai/gpt-oss-120b"
# Used when the main model is rate-limited, overloaded, or retired. It accepts the same
# request options and has its own free-tier limits on Groq.
LLM_FALLBACK_MODEL_NAME = "openai/gpt-oss-20b"

APP_NAME = "HealthForge AI"
APP_TAGLINE = "Evidence-based fitness, nutrition, and habit coaching powered by GPT-OSS on Groq."

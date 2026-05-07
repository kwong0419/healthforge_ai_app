# HealthForge AI

HealthForge AI is a portfolio-grade health, fitness, and nutrition LLM coach
built with:

- Python
- Streamlit
- Groq API
- Llama 3.3 Versatile

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Then, open the `.env` file and fill in your API keys:
   - `GROQ_API_KEY` (for the LLM coach)
   - `GEMINI_API_KEY` (for the vision features)

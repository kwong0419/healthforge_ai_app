# HealthForge AI

HealthForge AI is a portfolio-grade health, fitness, and nutrition LLM coach
built with:

- Python
- Streamlit
- Groq API
- Llama 3.3 Versatile

## Live App

The application is deployed on Streamlit Community Cloud and can be accessed here:
**[Link to App] (Replace this with your Streamlit App URL)**

> **Note on Inactivity:** Streamlit Community Cloud apps automatically go to sleep after a period of inactivity to conserve resources. If you visit the link and find the app is asleep, simply click the **"Yes, get this app back up!"** button on the screen. The app will wake up and be fully functional within 1-2 minutes.

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

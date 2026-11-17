import streamlit as st

# HealthForge's accent color. It's applied with CSS rather than Streamlit's theme
# setting, because setting a theme color makes Streamlit force light mode on everyone.
ACCENT = "#1D9E75"
ACCENT_DARK = "#0F6E56"
ACCENT_TINT = "rgba(29, 158, 117, 0.14)"

_CSS = f"""
<style>
/* Headings in the accent color */
h1, h2, h3, h4 {{ color: {ACCENT} !important; }}

/* Accent in place of Streamlit's default red */
button[data-testid="stBaseButton-primary"] {{
    background-color: {ACCENT} !important;
    border-color: {ACCENT} !important;
    color: #ffffff !important;
}}
button[data-testid="stBaseButton-primary"]:hover {{
    background-color: {ACCENT_DARK} !important;
    border-color: {ACCENT_DARK} !important;
}}
button[data-testid^="stBaseButton-secondary"]:hover,
button[data-testid^="stBaseButton-secondary"]:focus:not(:active) {{
    border-color: {ACCENT} !important;
    color: {ACCENT} !important;
}}
[data-baseweb="tab-highlight"] {{ background-color: {ACCENT} !important; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: {ACCENT} !important; }}
button[data-baseweb="tab"]:hover p {{ color: {ACCENT} !important; }}
label:has(input[type="checkbox"]:checked) > span:first-child {{
    background-color: {ACCENT} !important;
    border-color: {ACCENT} !important;
}}
[data-testid="stCheckbox"] label:has(input[role="switch"]:checked) > div:first-child,
label[data-baseweb="checkbox"]:has(input:checked) > div:first-child {{
    background-color: {ACCENT} !important;
}}
label[data-baseweb="radio"]:has(input:checked) > div:first-child {{
    background-color: {ACCENT} !important;
}}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within,
[data-baseweb="select"] > div:focus-within {{
    border-color: {ACCENT} !important;
}}
a {{ color: {ACCENT} !important; }}
[data-testid="stExpander"] summary:hover, [data-testid="stExpander"] summary:focus-visible,
[data-testid="stExpander"] summary:hover p, [data-testid="stExpander"] summary:hover svg {{
    color: {ACCENT} !important; fill: {ACCENT} !important;
}}

/* The day picker: a row of radio buttons drawn as pills */
.st-key-hf_day_picker [role="radiogroup"] {{ gap: 6px; flex-wrap: wrap; }}
.st-key-hf_day_picker label[data-baseweb="radio"] {{
    border: 1px solid rgba(128, 128, 128, 0.4); border-radius: 999px;
    padding: 2px 12px; margin: 0 !important;
}}
.st-key-hf_day_picker label[data-baseweb="radio"] > div:first-child {{ display: none; }}
.st-key-hf_day_picker label[data-baseweb="radio"]:has(input:checked) {{
    background-color: {ACCENT_TINT}; border-color: {ACCENT};
}}
.st-key-hf_day_picker label[data-baseweb="radio"]:has(input:checked) p {{ color: {ACCENT}; font-weight: 600; }}

/* Plan pieces */
.hf-chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0.25rem 0 0.75rem; }}
.hf-chip {{
    display: inline-block; padding: 1px 10px; border-radius: 999px; font-size: 0.85rem;
    background: {ACCENT_TINT}; border: 1px solid rgba(29, 158, 117, 0.45); white-space: nowrap;
}}
.hf-day-title {{ color: {ACCENT}; font-size: 1.15rem; font-weight: 600; margin: 0; line-height: 1.3; }}
.hf-day-sub {{ opacity: 0.7; font-size: 0.9rem; margin: 0; }}
.hf-item {{ padding: 0.6rem 0; border-top: 1px solid rgba(128, 128, 128, 0.22); }}
.hf-list .hf-item:first-child {{ border-top: none; padding-top: 0.2rem; }}
.hf-item-top {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
.hf-item-name {{ font-weight: 600; }}
.hf-item-notes {{ opacity: 0.7; font-size: 0.88rem; margin-top: 2px; }}
.hf-item-label {{ color: {ACCENT}; font-size: 0.8rem; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.04em; }}
.hf-demo {{ margin-left: auto; font-size: 0.85rem; white-space: nowrap; text-decoration: none; }}

/* The coach's reply to feedback: a glowing card that pops in when it's new */
[class*="st-key-hf_coach_reply"] {{
    border: 2px solid {ACCENT}; border-radius: 14px; padding: 1rem 1.1rem; box-sizing: border-box;
    background: linear-gradient(160deg, rgba(29, 158, 117, 0.20) 0%, rgba(29, 158, 117, 0.05) 55%);
    box-shadow: 0 6px 24px rgba(29, 158, 117, 0.25);
}}
/* Streamlit sizes elements to the column in pixels; fit them inside the card's padding */
[class*="st-key-hf_coach_reply"] [data-testid="stElementContainer"],
[class*="st-key-hf_coach_reply"] [style*="width"] {{ width: 100% !important; }}
.st-key-hf_coach_reply_fresh {{
    animation: hf-pop 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both, hf-glow 1.6s ease-out 0.55s 2;
}}
@keyframes hf-pop {{
    0% {{ opacity: 0; transform: translateY(16px) scale(0.94); }}
    100% {{ opacity: 1; transform: none; }}
}}
@keyframes hf-glow {{
    0% {{ box-shadow: 0 0 0 0 rgba(29, 158, 117, 0.55); }}
    100% {{ box-shadow: 0 0 0 14px rgba(29, 158, 117, 0), 0 6px 24px rgba(29, 158, 117, 0.25); }}
}}
@media (prefers-reduced-motion: reduce) {{
    .st-key-hf_coach_reply_fresh {{ animation: none; }}
}}
.hf-reply-head {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.hf-reply-icon {{
    display: inline-flex; align-items: center; justify-content: center; width: 2.2rem; height: 2.2rem;
    border-radius: 50%; background: {ACCENT}; font-size: 1.1rem;
}}
.hf-reply-title {{ color: {ACCENT}; font-size: 1.2rem; font-weight: 700; line-height: 1.25; }}
.hf-reply-count {{
    background: {ACCENT}; color: #ffffff; border-radius: 999px; padding: 1px 10px;
    font-size: 0.8rem; font-weight: 600; white-space: nowrap;
}}
.hf-asked {{ opacity: 0.7; font-size: 0.88rem; font-style: italic; margin-bottom: 0.5rem; }}
.hf-coach-note {{ border-left: 4px solid {ACCENT}; background: rgba(128, 128, 128, 0.10); border-radius: 8px;
                 padding: 0.7rem 0.9rem; margin-bottom: 0.75rem; font-size: 1.02rem; }}
.hf-coach-note p {{ margin: 0 0 0.4rem; }}
.hf-coach-note p:last-child {{ margin-bottom: 0; }}
.hf-change-head {{ font-weight: 700; margin-bottom: 0.25rem; }}
.hf-change-title {{ color: {ACCENT}; font-size: 0.85rem; font-weight: 600; margin-top: 0.5rem; }}
.hf-change-list {{ margin: 0.1rem 0 0 1.1rem; padding: 0; }}
.hf-change-list li {{ margin: 0.1rem 0; font-size: 0.92rem; }}
.hf-change-list li::marker {{ color: {ACCENT}; }}

/* Streamlit stacks columns on phones. Inside containers keyed "hf_inline_...", keep them
   side by side (e.g. Sets and Reps, or a title and its Edit button). */
[class*="st-key-hf_inline_"] [data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    gap: 0.5rem !important;
}}
[class*="st-key-hf_inline_"] [data-testid="stColumn"] {{ min-width: 0 !important; }}
/* A toggle at the end of such a row sits at the right edge */
[class*="st-key-hf_inline_"] [data-testid="stColumn"]:last-child [data-testid="stCheckbox"] {{
    display: flex; justify-content: flex-end;
}}
</style>
"""


def inject_styles() -> None:
    """Adds HealthForge's look (accent color, plan cards) to the page. Call once per run."""
    st.markdown(_CSS, unsafe_allow_html=True)

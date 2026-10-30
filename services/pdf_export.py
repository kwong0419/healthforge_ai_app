"""
Builds a clean, printable PDF of a user's full plan.
"""

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

from fontTools.ttLib import TTFont
from fpdf import FPDF
from fpdf.fonts import FontFace

from services.exercise_links import exercise_demo_url
from services.planner import failed_safety_audit
from services.plan_storage import PDF_ATTACHMENT_NAME

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILY = "DejaVu"

ACCENT = (16, 122, 87)
TEXT = (33, 37, 41)
MUTED = (108, 117, 125)
TABLE_HEADER_FILL = (232, 245, 239)
WARNING_FILL = (255, 243, 205)
WARNING_TEXT = (102, 77, 3)

LINE_HEIGHT = 5.5


@lru_cache(maxsize=1)
def _supported_codepoints() -> frozenset:
    """Characters the bundled font can draw (anything else, like emoji, is dropped)."""
    cmap = TTFont(FONT_DIR / "DejaVuSans.ttf").getBestCmap()
    return frozenset(cmap.keys())


def _clean(value: Any) -> str:
    if value is None:
        return ""
    supported = _supported_codepoints()
    return "".join(ch for ch in str(value) if ord(ch) in supported or ch == "\n").strip()


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return [value] if value else []


class PlanPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="Letter")
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)
        self.add_font(FONT_FAMILY, "", FONT_DIR / "DejaVuSans.ttf")
        self.add_font(FONT_FAMILY, "B", FONT_DIR / "DejaVuSans-Bold.ttf")
        self.add_font(FONT_FAMILY, "I", FONT_DIR / "DejaVuSans-Oblique.ttf")
        self.set_text_color(*TEXT)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font(FONT_FAMILY, "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 5, "HealthForge AI · For general fitness guidance only, not medical advice")
        self.set_x(self.l_margin)
        self.cell(0, 5, f"Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(*TEXT)

    # --- Building blocks -------------------------------------------------

    def section_title(self, title: str) -> None:
        self._keep_space(30)
        self.ln(3)
        self.set_font(FONT_FAMILY, "B", 16)
        self.set_text_color(*ACCENT)
        self.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.set_text_color(*TEXT)
        self.ln(4)

    def subheading(self, text: str, keep_space: float = 25) -> None:
        self._keep_space(keep_space)
        self.set_font(FONT_FAMILY, "B", 12)
        self.multi_cell(0, 7, _clean(text), new_x="LMARGIN", new_y="NEXT", align="L")

    def paragraph(self, text: Any, style: str = "", size: float = 10, color=TEXT) -> None:
        text = _clean(text)
        if not text:
            return
        self.set_font(FONT_FAMILY, style, size)
        self.set_text_color(*color)
        self.multi_cell(0, LINE_HEIGHT, text, new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(*TEXT)
        self.ln(1.5)

    def bullets(self, items: Iterable[Any]) -> None:
        self.set_font(FONT_FAMILY, "", 10)
        for item in items:
            text = _clean(item)
            if not text:
                continue
            self.set_x(self.l_margin + 2)
            self.cell(5, LINE_HEIGHT, "•")
            self.multi_cell(0, LINE_HEIGHT, text, new_x="LMARGIN", new_y="NEXT", align="L")
            self.ln(0.8)
        self.ln(1.5)

    def checklist(self, items: Iterable[Any], columns: int = 2) -> None:
        """Printable tick-box list laid out in columns, filled top to bottom."""
        items = [text for text in (_clean(i) for i in items) if text]
        if not items:
            return
        self.set_font(FONT_FAMILY, "", 10)
        col_width = (self.w - self.l_margin - self.r_margin) / columns
        text_width = col_width - 7
        rows = (len(items) + columns - 1) // columns
        for r in range(rows):
            row_items = [(c, items[c * rows + r]) for c in range(columns) if c * rows + r < len(items)]
            row_height = max(self._text_height(text, text_width) for _, text in row_items)
            self._keep_space(row_height + 1)
            y = self.get_y()
            for c, text in row_items:
                x = self.l_margin + c * col_width
                self.set_draw_color(*MUTED)
                self.set_line_width(0.3)
                self.rect(x, y + 1.3, 3, 3)
                self.set_xy(x + 5, y)
                self.multi_cell(text_width, LINE_HEIGHT, text, align="L")
            self.set_xy(self.l_margin, y + row_height + 1)
        self.ln(2)

    def table(
        self,
        headings: List[str] | None,
        rows: List[List[Any]],
        col_widths: List[int],
        links: List[str | None] | None = None,
    ) -> None:
        """links, if given, makes each row's first cell a clickable link."""
        if not rows:
            return
        self.set_font(FONT_FAMILY, "", 9)
        self.set_draw_color(210, 214, 218)
        self.set_line_width(0.2)
        with super().table(
            col_widths=col_widths,
            line_height=LINE_HEIGHT,
            padding=1.5,
            headings_style=FontFace(emphasis="BOLD", fill_color=TABLE_HEADER_FILL, color=ACCENT),
            first_row_as_headings=bool(headings),
            text_align="LEFT",
            v_align="TOP",
        ) as table:
            if headings:
                header = table.row()
                for h in headings:
                    header.cell(h)
            for r, values in enumerate(rows):
                row = table.row()
                link = links[r] if links else None
                for c, value in enumerate(values):
                    if c == 0 and link:
                        row.cell(_clean(value), link=link, style=FontFace(color=ACCENT, emphasis="UNDERLINE"))
                    else:
                        row.cell(_clean(value))
        self.ln(4)

    def callout(self, text: str) -> None:
        self.set_font(FONT_FAMILY, "B", 10)
        self.set_fill_color(*WARNING_FILL)
        self.set_text_color(*WARNING_TEXT)
        self.multi_cell(0, LINE_HEIGHT + 0.5, _clean(text), fill=True, padding=3, new_x="LMARGIN", new_y="NEXT", align="L")
        self.set_text_color(*TEXT)
        self.set_fill_color(255, 255, 255)  # Don't let the callout's fill leak into later tables
        self.ln(3)

    def _keep_space(self, height: float) -> None:
        """Start a new page if fewer than `height` mm remain, so headings aren't orphaned."""
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def _text_height(self, text: str, width: float) -> float:
        lines = self.multi_cell(width, LINE_HEIGHT, text, dry_run=True, output="LINES", align="L")
        return len(lines) * LINE_HEIGHT


def build_plan_pdf(plan: Dict[str, Any], profile: Dict[str, Any] | None, save_data: str | None = None) -> bytes:
    """
    Renders the full plan (workout, nutrition, habits, disclaimers) as PDF bytes.
    If save_data (a serialized plan file) is given, it's attached inside the PDF so
    the PDF can be uploaded back into HealthForge to restore the plan.
    """
    profile = profile or {}
    pdf = PlanPDF()
    pdf.set_title("HealthForge AI Personal Plan")
    pdf.set_author("HealthForge AI")
    pdf.add_page()

    _render_cover(pdf, plan, profile)
    _render_workout(pdf, plan.get("workout_plan") or {})
    _render_nutrition(pdf, plan.get("nutrition_plan") or {})
    _render_habits(pdf, plan.get("habits_and_lifestyle") or {})
    _render_disclaimers(pdf, plan.get("disclaimers"))

    if save_data:
        pdf.embed_file(
            bytes=save_data.encode("utf-8"),
            basename=PDF_ATTACHMENT_NAME,
            mime_type="application/json",
            desc="HealthForge plan data (upload this PDF to HealthForge to reload your plan)",
        )

    return bytes(pdf.output())


def _render_cover(pdf: PlanPDF, plan: Dict[str, Any], profile: Dict[str, Any]) -> None:
    name = _clean(profile.get("name")).strip()

    pdf.set_font(FONT_FAMILY, "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 6, "HEALTHFORGE AI", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, "B", 22)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(0, 11, f"Personal Plan for {name}" if name else "Your Personal Plan", new_x="LMARGIN", new_y="NEXT", align="L")
    today = date.today()
    pdf.paragraph(f"Prepared {today:%B} {today.day}, {today.year}", size=9, color=MUTED)

    secondary = profile.get("secondary_goal")
    goal = profile.get("primary_goal")
    days = profile.get("days_per_week")
    training = " · ".join(
        p for p in [f"{days} days/week" if days else "", _clean(profile.get("session_length"))] if p
    )
    diet = " · ".join(
        p for p in [_clean(profile.get("diet_preference")), _clean(profile.get("diet_restrictions"))] if p
    )
    snapshot = [
        ("Goal", f"{goal} (secondary: {secondary})" if goal and secondary else goal),
        ("Experience", profile.get("experience_level")),
        ("Training", training),
        ("Equipment", ", ".join(_as_list(profile.get("equipment")))),
        ("Injuries / limitations", profile.get("limitations")),
        ("Diet", diet),
    ]
    rows = [[label, value] for label, value in snapshot if _clean(value)]
    if rows:
        pdf.ln(1)
        pdf.set_font(FONT_FAMILY, "B", 12)
        pdf.cell(0, 7, "Your Profile", new_x="LMARGIN", new_y="NEXT")
        pdf.table(None, rows, col_widths=[28, 72])

    if failed_safety_audit(plan):
        pdf.callout(
            "Heads up: this plan didn't pass HealthForge's automated safety check. Review it "
            "carefully, especially around your injuries and limitations. See Safety & Disclaimers "
            "at the end for the specific concern."
        )

    if plan.get("summary"):
        pdf.subheading("Overview")
        pdf.paragraph(plan["summary"])


def _render_workout(pdf: PlanPDF, workout: Dict[str, Any]) -> None:
    days = _as_list(workout.get("weekly_split"))
    if not days and not workout.get("progression_notes"):
        return

    pdf.section_title("Workout Plan")
    pdf.paragraph("Tap an exercise name to watch demo videos of it.", style="I", size=9, color=MUTED)
    for day in days:
        if not isinstance(day, dict):
            pdf.paragraph(day)
            continue
        pdf.subheading(day.get("day") or "Workout", keep_space=40)
        pdf.paragraph(day.get("focus"), style="I", size=9.5, color=MUTED)

        rows, links = [], []
        for ex in _as_list(day.get("exercises")):
            if isinstance(ex, dict):
                name = ex.get("name") or "Exercise"
                rows.append([name, ex.get("sets"), ex.get("reps"), ex.get("notes")])
                links.append(exercise_demo_url(name))
            else:
                rows.append([ex, "", "", ""])
                links.append(None)
        pdf.table(["Exercise", "Sets", "Reps", "Notes"], rows, col_widths=[34, 9, 13, 44], links=links)

    if workout.get("progression_notes"):
        pdf.subheading("Progression Notes")
        pdf.paragraph(workout["progression_notes"])


def _render_nutrition(pdf: PlanPDF, nutrition: Dict[str, Any]) -> None:
    meals = _as_list(nutrition.get("daily_structure"))
    groceries = _as_list(nutrition.get("grocery_list"))
    if not (nutrition.get("philosophy") or meals or groceries):
        return

    pdf.add_page()
    pdf.section_title("Nutrition Plan")
    if nutrition.get("philosophy"):
        pdf.subheading("Approach")
        pdf.paragraph(nutrition["philosophy"])

    if meals:
        pdf.subheading("Daily Meal Structure")
        rows = [
            [m.get("meal") or "Meal", m.get("example"), m.get("notes")] if isinstance(m, dict) else [m, "", ""]
            for m in meals
        ]
        pdf.table(["Meal", "Example", "Notes"], rows, col_widths=[18, 41, 41])

    if groceries:
        pdf.subheading("Grocery List")
        pdf.checklist(groceries)


def _render_habits(pdf: PlanPDF, habits: Dict[str, Any]) -> None:
    sections = [
        ("Sleep", habits.get("sleep")),
        ("Stress Management", habits.get("stress_management")),
        ("Daily Habits", habits.get("daily_habits")),
    ]
    sections = [(title, _as_list(items)) for title, items in sections if _as_list(items)]
    if not sections:
        return

    pdf.section_title("Habits & Lifestyle")
    for title, items in sections:
        pdf.subheading(title)
        pdf.bullets(items)


def _render_disclaimers(pdf: PlanPDF, disclaimers: Any) -> None:
    pdf.section_title("Safety & Disclaimers")
    pdf.bullets(_as_list(disclaimers))
    pdf.paragraph(
        "This plan was generated by AI for general fitness and wellness guidance. It is not "
        "medical advice. Consult a qualified healthcare professional before starting a new "
        "exercise or nutrition program, especially if you have injuries or health conditions.",
        size=9,
        color=MUTED,
    )

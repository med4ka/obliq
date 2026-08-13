"""DESIGN.md tokens + Streamlit CSS injection.

Palette is fixed ("Sertifikat") -- light mode only. Green/red are never used
for up/down moves (DESIGN.md 1); changes are shown as arrow + neutral number.

Fonts (DESIGN.md 2): Source Serif 4 / IBM Plex Sans / IBM Plex Mono. Plotly
figures set their own font (charts.py); this module covers Streamlit chrome.
"""
from __future__ import annotations

import streamlit as st

# ---- DESIGN.md 1: Base palette "Kertas Sertifikat" ----
PARCHMENT = "#F6F1E7"
INK = "#1F2419"
INK_MUTED = "#6B6355"
LEDGER_GREEN = "#0F4C3A"
SURFACE = "#FFFEF9"
SEAL_RED = "#8C2F1F"  # anomaly flags only (DESIGN.md 1); unused in Fase 1 UI
GOLD_VERIFIED = "#A67C27"  # verified-source accent; reserved

# ---- DESIGN.md 2: typeface families (loaded via Google Fonts in CSS) ----
FONT_HEADING = "Source Serif 4", "Libre Caslon", "Georgia", "serif"
FONT_BODY = "IBM Plex Sans", "Public Sans", "system-ui", "sans-serif"
FONT_MONO = "IBM Plex Mono", "Consolas", "monospace"

# RULES.md 3 -- badge shown whenever source starts with "DUMMY"/unknown.
DUMMY_BADGE = "DATA CONTOH — BELUM DARI SUMBER RESMI"

# ---- Number formatting (display only; data stays Decimal/string in API) ----
def fmt_pct(value: float | None, ndigits: int = 2) -> str:
    """Percent with Indonesian decimal separator, e.g. 6.84 -> '6,84%'."""
    if value is None:
        return "—"
    return f"{value:.{ndigits}f}".replace(".", ",") + "%"


def fmt_years(value: float | None) -> str:
    """Tenor display: 9.89 -> '9,9 th'."""
    if value is None:
        return "—"
    return f"{value:.1f}".replace(".", ",") + " th"


def _css() -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap');

/* App shell -- kertas sertifikat */
.stApp {{
    background-color: {PARCHMENT};
    color: {INK};
}}
html, body, [class*="st-"] {{
    font-family: {", ".join(FONT_BODY)};
}}

/* Sidebar */
[data-testid="stSidebar"] {{
    background-color: {SURFACE};
    border-right: 1px solid #E4DECE;
}}

/* Headings -- serif dokumen resmi */
h1, h2, h3, h4, [data-testid="stHeader"] {{
    font-family: {", ".join(FONT_HEADING)};
    color: {INK};
}}

/* Tables/numbers -- tabular mono */
table, [data-testid="stDataFrame"] span, [data-testid="stMetricValue"], .mono {{
    font-family: {", ".join(FONT_MONO)};
}}

/* Secondary text */
[data-testid="stCaptionContainer"], .stCaption, p, li {{
    color: {INK_MUTED};
}}

/* Links reuse the ledger-green accent */
a {{
    color: {LEDGER_GREEN};
}}

/* Dummy badge styling -- always prominent, never subtle */
.dummy-badge {{
    font-family: {", ".join(FONT_HEADING)};
    font-weight: 600;
    color: {SEAL_RED};
}}

/* Card look for panels */
.obliq-card {{
    background-color: {SURFACE};
    border: 1px solid #E4DECE;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.5rem;
}}
</style>
"""


def inject() -> None:
    """Inject so theme survives reruns; call once after set_page_config."""
    st.markdown(_css(), unsafe_allow_html=True)
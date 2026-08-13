"""Obliq dashboard helper modules.

`api_client` — read-only calls to the FastAPI layer (never the DB directly,
per ARCHITECTURE.md 1). `styling` — DESIGN.md palette & fonts injected into
Streamlit. `charts` — Plotly figure builders (hero curve, time series with
explicit gaps, step chart for policy rate, skeleton placeholder).
"""
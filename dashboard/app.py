"""Obliq dashboard - minimal Fase 0 page.

Reads macro_indicators from local DB and renders a simple table.
Per RULES.md 3: any row whose source is empty/unknown OR starts with 'DUMMY'
must show a prominent badge and must never be mixed silently with real data.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db.connection import get_engine

st.set_page_config(page_title="Obliq - Indikator Makro", layout="centered")

DUMMY_BADGE = "DATA CONTOH — BELUM DARI SUMBER RESMI"


def is_dummy_or_unknown(source: object) -> bool:
    """True for rows that must not be presented as authoritative data."""
    if source is None or str(source).strip() == "":
        return True
    return str(source).startswith("DUMMY")


def load_macro_indicators() -> pd.DataFrame:
    query = text(
        "SELECT indicator_type, observation_date, value, source, fetched_at "
        "FROM macro_indicators ORDER BY observation_date"
    )
    with get_engine().connect() as conn:
        return pd.read_sql(query, conn)


def main() -> None:
    st.title("Obliq — Indikator Makro")

    df = load_macro_indicators()

    if df.empty:
        st.info("Data tidak tersedia.")
        return

    dummy_mask = df["source"].map(is_dummy_or_unknown)
    any_dummy = bool(dummy_mask.any())

    if any_dummy:
        st.error(f"⚠️ {DUMMY_BADGE}")
        st.caption(
            "Tabel di bawah berisi data contoh (source=DUMMY_CONTOH), bukan angka "
            "resmi dari BPS/BI. Tidak boleh dipakai untuk keputusan finansial."
        )

    display = df.copy()
    display["status"] = display["source"].map(
        lambda s: DUMMY_BADGE if is_dummy_or_unknown(s) else "Data resmi"
    )
    display["value"] = display["value"].map(lambda v: f"{v:.4f}%")

    st.dataframe(
        display,
        width="stretch",
        hide_index=True,
        column_config={"status": st.column_config.TextColumn("Status")},
    )

    st.caption(f"Source: {', '.join(df['source'].astype(str).unique())}")


if __name__ == "__main__":
    main()
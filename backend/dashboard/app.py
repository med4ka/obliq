"""Obliq dashboard (Streamlit) -- Fase 1, page structure.

Reads ONLY through the FastAPI layer (ARCHITECTURE.md 1); never touches the DB
or external sources. DESIGN.md rules enforced: parchment/ink/ledger-green
palette, hero yield curve first, every chart carries a "Sumber: ... · Data per
..." caption, gaps render broken (connectgaps=False), dummy rows carry the
RULES.md 3 badge, and up/down moves are shown as arrow + neutral number.

Run:  streamlit run dashboard/app.py   (API must be up: uvicorn api.main:app)
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

from dashboard.lib import api_client, charts, styling
from dashboard.lib.api_client import ApiClientError

st.set_page_config(
    page_title="Obliq — Pasar Obligasi Indonesia",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

styling.inject()

INDICATOR_DISPLAY = {
    "inflation_yoy": "Inflasi (IHK, YoY)",
    "bi_7drr": "BI7DRR (suku bunga acuan)",
    "usd_idr": "Kurs USD/IDR (JISDOR)",
}

PAGE = st.sidebar.radio(
    "Navigasi",
    ["Kurva Yield", "Indikator Makro", "Belajar"],
    label_visibility="collapsed",
)


def caption(source: str, as_of: dt.date | str | None) -> None:
    """Mandatory source + as-of caption (SYSTEM.md 1.2-1.3, DESIGN.md 4)."""
    st.caption(f"Sumber: {source} · Data per {as_of if as_of is not None else '—'}")


def render_fetch(key: str, fetcher, builder) -> None:
    """Fetch via API, show skeleton while loading, chart on success.

    Streamlit has no native chart-skeleton slot; we approximate DESIGN.md 4 with
    a wavy placeholder rendered before the network call, replaced in place when
    the data arrives. On error the placeholder is replaced by a clear, honest
    message (never a fabricated curve).
    """
    slot = st.empty()
    with slot.container():
        st.plotly_chart(
            charts.skeleton_fig(),
            width="stretch",
            config={"displayModeBar": False},
            key=f"skeleton_{key}",
        )
    try:
        payload = fetcher()
    except ApiClientError as exc:
        slot.warning(str(exc))
        return
    if payload.get("status") == "empty":
        slot.warning(str(payload.get("message") or "Data tidak tersedia."))
        return
    if payload.get("status") in ("error", "not_found"):
        slot.error(str(payload.get("message") or "Data tidak ditemukan."))
        return
    slot.empty()  # clear skeleton before rendering the real figure
    with slot.container():
        builder(payload)
    return payload


# --------------------------------------------------------------------------
# Halaman 1: Kurva Yield (hero)
# --------------------------------------------------------------------------
def page_curve() -> None:
    st.header("Kurva Yield Surat Utang Negara (SUN)")
    st.caption(
        "Yield rata-rata tertimbang hasil lelang (Weighted Average Rate), per seri, "
        "dari observasi lelang terbaru tiap obligasi aktif. Bukan harga pasar intraday."
    )

    def builder(payload: dict) -> None:
        items = payload.get("items", [])
        if not items:
            st.info(str(payload.get("message") or "Belum ada data kurva."))
            return
        st.plotly_chart(
            charts.current_curve_fig(items),
            width="stretch",
            config={"displayModeBar": False},
        )
        per_bond_as_of = sorted({it.get("observation_date") for it in items}, reverse=True)
        caption("DJPPR (Kemenkeu) — hasil lelang SUN", payload.get("as_of"))
        if len(per_bond_as_of) > 1:
            st.caption(
                f"Kurva ini menggabungkan {len(per_bond_as_of)} tanggal lelang berbeda "
                f"(observasi paling lama: {per_bond_as_of[-1]})."
            )

    _ = render_fetch("curve", api_client.current_curve, builder)

    st.divider()
    st.subheader("Histori Yield Satu Seri")
    st.caption(
        "Pilih seri untuk melihat yield di tiap lelang. Rentang tanpa lelang dilapisi "
        "garis putus (tidak disambung)."
    )
    code = st.text_input("Kode seri (mis. FR0108)", "FR0108")
    if code:

        def hbuilder(payload: dict) -> None:
            items = payload.get("items", [])
            if not items:
                st.info(str(payload.get("message") or "Tidak ada histori."))
                return
            st.plotly_chart(
                charts.curve_history_fig(items, code.upper()),
                width="stretch",
                config={"displayModeBar": False},
            )
            last = max((it.get("observation_date") for it in items), default=None)
            sources = sorted({it.get("source") for it in items})
            caption("DJPPR (Kemenkeu) — hasil lelang SUN", last)
            st.caption(f"{len(items)} observasi lelang · Sumber: {', '.join(sources)}")

        render_fetch(f"history_{code}", lambda: api_client.bond_history(code.upper()), hbuilder)


# --------------------------------------------------------------------------
# Halaman 2: Indikator Makro
# --------------------------------------------------------------------------
def page_macro() -> None:
    st.header("Indikator Makroekonomi")
    st.caption(
        "Konteks suku bunga dan inflasi. Data dari BPS & Bank Indonesia; angka "
        "dibaca sebagai observasi, bukan rekomendasi (SYSTEM.md 1.4)."
    )

    # Inflasi (real + dummy dipisah)
    st.subheader("Inflasi — Indeks Harga Konsumen (YoY)")
    st.caption("Perubahan IHK bulan ini vs bulan yang sama tahun lalu. Dihitung sendiri oleh pipeline dari indeks IHK (PRD.md 1).")

    def inf_builder(payload: dict) -> None:
        items = payload.get("items", [])
        real = [it for it in items if not it.get("is_dummy")]
        dummy = [it for it in items if it.get("is_dummy")]
        if not items:
            st.info(str(payload.get("message") or "Tidak ada data inflasi."))
            return
        st.plotly_chart(
            charts.inflation_fig(real, dummy),
            width="stretch",
            config={"displayModeBar": False},
        )
        max_date = max((it.get("observation_date") for it in items), default=None)
        # Honest source line: dummy split out (RULES.md 3).
        caption(
            "BPS (web API, var IHK) untuk data resmi; dummy tidak dihitung ke resmi",
            max_date,
        )
        if dummy:
            st.error(styling.DUMMY_BADGE)
            st.caption(f"{len(dummy)} titik 2026 berasal dari source=DUMMY_CONTOH. Ini contoh, bukan "
                "statistik resmi BPS — ditampilkan terpisah (diamond terbuka), tidak "
                "dicampur dengan data resmi.")

    _ = render_fetch("inflation", lambda: api_client.macro_history("inflation_yoy"), inf_builder)

    st.divider()

    # BI7DRR: step chart (policy rate holds)
    st.subheader("BI7DRR — Suku Bunga Acuan Bank Indonesia")
    st.caption("Nilai berlaku sampai pengumuman kebijakan berikutnya — digambar sebagai tangga, bukan garis tipis yang terkesan data hilang.")

    def bi_builder(payload: dict) -> None:
        items = payload.get("items", [])
        if not items:
            st.info(str(payload.get("message") or "Tidak ada data BI7DRR."))
            return
        st.plotly_chart(
            charts.step_rate_fig(items, "BI7DRR"),
            width="stretch",
            config={"displayModeBar": False},
        )
        last = max((it.get("observation_date") for it in items), default=None)
        caption("Bank Indonesia — BI7DRR", last)

    _ = render_fetch("bi7drr", lambda: api_client.macro_history("bi_7drr"), bi_builder)

    st.divider()

    # JISDOR USD/IDR
    st.subheader("Kurs Referensi USD/IDR (JISDOR)")
    st.caption("Kurs tengah Bank Indonesia untuk transaksi antar bank.")

    def jisdor_builder(payload: dict) -> None:
        items = payload.get("items", [])
        if not items:
            st.info(str(payload.get("message") or "Tidak ada data JISDOR."))
            return
        st.plotly_chart(
            charts.daily_series_fig(items, "Kurs USD/IDR (JISDOR)"),
            width="stretch",
            config={"displayModeBar": False},
        )
        last = max((it.get("observation_date") for it in items), default=None)
        caption("Bank Indonesia — JISDOR", last)

    _ = render_fetch("jisdor", lambda: api_client.macro_history("usd_idr"), jisdor_builder)


# --------------------------------------------------------------------------
# Halaman 3: Belajar (glossary dari PRD.md 1)
# --------------------------------------------------------------------------
def page_learn() -> None:
    st.header("Belajar — Dasar Obligasi", help="Glossary dari PRD.md 1")

    glossary = [
        ("Obligasi (bond)", "Surat utang: penerbit (pemerintah/perusahaan) pinjam uang dari investor, janji bayar kupon berkala dan mengembalikan pokok di jatuh tempo. Beda dari saham — bukan kepemilikan, cuma pinjaman."),
        ("Sukuk", "Versi syariah obligasi: secara legal beda (bagi hasil/sewa aset, bukan bunga) tapi secara fungsi ekonomi mirip. Indonesia = penerbit Sukuk negara terbesar di dunia."),
        ("Tenor", "Jangka waktu sampai jatuh tempo. Obligasi 10 tahun = tenor 10 tahun."),
        ("Kupon (coupon rate)", "Persentase bunga TETAP dari nilai nominal, dicetak di kontrak, tidak berubah. Beda dari yield."),
        ("Yield", "Imbal hasil EFEKTIF bila beli sekarang di harga pasar dan pegang sampai jatuh tempo — memperhitungkan harga beli. Harga turun ⇒ yield naik; harga dan yield selalu bergerak berlawanan arah."),
        ("Kurva yield", "Grafik yield vs tenor untuk satu penerbit. Normalnya naik (tenor panjang = kompensasi risiko waktu lebih besar). Pembalikan kurva (tenor pendek > tenor panjang) secara historis sering mendahului resesi."),
        ("Credit spread", "Selisih (dalam bps) yield obligasi korporasi dikurangi yield obligasi pemerintah di tenor yang sama. Pemerintah dianggap risk-free, jadi spread ≈ premi risiko kredit perusahaan (Fase 3)."),
        ("Basis poin (bps)", "1 bps = 0.01%. Dipakai karena perubahan yield/spread biasanya kecil; 'spread melebar 45 bps' lebih presisi daripada '0.45%'."),
        ("Lelang (auction)", "Penerbitan SUN: dealer utama menawar via sistem lelang BI, pemerintah memilih (award) yang terbaik. Per seri dihasilkan Weighted Average Yield — inilah yang dipakai kurva yield, BUKAN kupon."),
        ("SPN", "Obligasi pemerintah jangka pendek (< 1 th). Dijual diskonto (tanpa kupon), jadi coupon_rate kosong di DB."),
        ("FR (Fixed-Rate)", "Seri SUN jangka panjang dengan kupon tetap — seri benchmark pembentuk kurva. Sering di-reopen (lelang ulang), jadi satu kode FR muncul di banyak tanggal."),
        ("Bid-to-cover ratio", "Total penawaran ÷ yang dimenangkan. Angka > 1 = lelang terisi; > 2–3 sering dianggap indikator permintaan kuat."),
        ("IHK", "Indeks Harga Konsumen: tingkat harga rata-rata barang konsumsi, angka indeks (bukan %), dasar 2018=100 untuk 90 kota Indonesia. Bahan baku inflasi."),
        ("Inflasi YoY vs MtM", "YoY: IHK bulan ini vs bulan SAMA tahun lalu — tren 12 bulan, tak terpengaruh musiman. MtM: vs bulan SEBELUMNYA — tekanan paling baru tapi lebih berisik karena musiman (Lebaran, tahun ajaran)."),
    ]

    for term, desc in glossary:
        with st.expander(term):
            st.markdown(desc)


# --------------------------------------------------------------------------
if PAGE == "Kurva Yield":
    page_curve()
elif PAGE == "Indikator Makro":
    page_macro()
else:
    page_learn()
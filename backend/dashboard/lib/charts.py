"""Plotly figure builders (DESIGN.md 4).

Shared chart rules enforced here once:
- Palette only from DESIGN.md tokens (never terminal green/red). The single
  accent line color is `ledger-green`; up/down values are plain neutral text,
  direction is shown with an arrow character in the UI layer, not via color.
- Time series render with `connectgaps=False`: missing-date ranges stay visibly
  broken instead of being silently joined (ARCHITECTURE.md 4, DESIGN.md 4).
- Every chart that reaches the UI goes through `caption()`, which must carry a
  "Sumber: ... · Data per ..." line -- enforced by convention in app.py.
- Skeleton placeholder is a wavy grey chart-shaped figure (DESIGN.md 4),
  rendered while data is being fetched.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go

from dashboard.lib import styling

_GRID = "#E7E0CE"
_AXIS = "#B4AC98"


def base_layout(fig: go.Figure, *, height: int = 420, x_title: str, y_title: str) -> go.Figure:
    """Apply Obliq styling to a figure: parchment area, subtle grid, mono ticks."""
    fig.update_layout(
        height=height,
        paper_bgcolor=styling.PARCHMENT,
        plot_bgcolor=styling.SURFACE,
        font={"family": ", ".join(styling.FONT_BODY), "color": styling.INK},
        margin={"l": 8, "r": 8, "t": 16, "b": 8},
        hovermode="closest",
        showlegend=True,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.25,
            "xanchor": "left",
            "x": 0,
            "font": {"family": ", ".join(styling.FONT_BODY), "color": styling.INK_MUTED},
        },
    )
    fig.update_xaxes(
        title={"text": x_title, "font": {"family": ", ".join(styling.FONT_BODY)}},
        showgrid=True,
        gridcolor=_GRID,
        linecolor=_AXIS,
        tickfont={"family": ", ".join(styling.FONT_MONO)},
    )
    fig.update_yaxes(
        title={"text": y_title},
        showgrid=True,
        gridcolor=_GRID,
        linecolor=_AXIS,
        tickfont={"family": ", ".join(styling.FONT_MONO)},
        ticksuffix="",
    )
    return fig


def skeleton_fig(height: int = 420) -> go.Figure:
    """Wavy grey chart-shaped placeholder (DESIGN.md 4), not a generic block."""
    x = [i / 10 for i in range(0, 61)]  # 0..6
    fig = go.Figure()
    for phase, amp in ((0.0, 0.18), (1.3, 0.24), (2.6, 0.15)):
        y = [
            0.5 + amp * math.sin(1.4 * xi + phase) + 0.08 * math.cos(2.1 * xi)
            for xi in x
        ]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line={"color": "#D9D2BE", "width": 2},
                hoverinfo="skip",
            )
        )
    fig.update_layout(
        height=height,
        paper_bgcolor=styling.PARCHMENT,
        plot_bgcolor=styling.SURFACE,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        xaxis={"visible": False, "range": [0, 6]},
        yaxis={"visible": False, "range": [0, 1]},
        showlegend=False,
    )
    return fig


def empty_fig(message: str, height: int = 300) -> go.Figure:
    """Honest 'no data' figure (SYSTEM.md 1.1): never fabricate a curve."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        font={"family": ", ".join(styling.FONT_BODY), "size": 15, "color": styling.INK_MUTED},
    )
    fig.update_layout(
        height=height,
        paper_bgcolor=styling.PARCHMENT,
        plot_bgcolor=styling.SURFACE,
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        xaxis={"visible": False},
        yaxis={"visible": False},
    )
    return fig


def current_curve_fig(items: list[dict]) -> go.Figure:
    """Hero chart: tenor (x) vs yield (y) for the current government curve.

    Points are the latest auction result per bond; no gradient fill, line is a
    thin ledger-green connector so the curve shape reads at a glance.
    """
    pts = [it for it in items if it.get("yield_value") is not None]
    ordered = sorted(
        pts, key=lambda it: (it.get("tenor_years") is None, it.get("tenor_years") or 0)
    )
    xs = [it.get("tenor_years") for it in ordered]
    ys = [it["yield_value"] for it in ordered]

    # Pre-format hover strings: avoids d3 format crashes when coupon/maturity
    # are None (SPN zero-coupon has no coupon_rate) and keeps SPN honest.
    def hover(it: dict) -> str:
        coupon = styling.fmt_pct(it.get("coupon_rate"))
        maturity = it.get("maturity_date") or "—"
        obs = str(it.get("observation_date"))
        tenor = styling.fmt_years(it.get("tenor_years"))
        return (
            f"<b>{it.get('bond_code')}</b> — {it.get('bond_name')}<br>"
            f"Tenor: {tenor} · Yield: {it['yield_value']:.4f}%<br>"
            f"Kupon: {coupon} · Jatuh tempo: {maturity}<br>"
            f"Observasi: {obs} · Sumber: {it.get('source')}"
        )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers+lines",
            line={"color": styling.LEDGER_GREEN, "width": 2},
            marker={
                "color": styling.LEDGER_GREEN,
                "size": 7,
                "line": {"color": styling.SURFACE, "width": 1},
            },
            text=[hover(it) for it in ordered],
            hoverinfo="text",
            name="Kurva yield",
        )
    )
    base_layout(fig, height=460, x_title="Tenor (tahun)", y_title="Yield W.A.R. (%)")
    fig.update_xaxes(tickformat=".1f")
    fig.update_yaxes(tickformat=".2f")
    return fig


def curve_history_fig(items: list[dict], bond_code: str) -> go.Figure:
    """One series' yield over time -- gaps stay broken (connectgaps=False)."""
    items = [it for it in items if it.get("yield_value") is not None]
    xs = [it.get("observation_date") for it in items]
    ys = [it["yield_value"] for it in items]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            connectgaps=False,
            line={"color": styling.LEDGER_GREEN, "width": 2},
            marker={"color": styling.LEDGER_GREEN, "size": 6},
            text=[
                (
                    f"<b>{it.get('source')}</b><br>{it.get('observation_date')}"
                    f"<br>Yield: {it['yield_value']:.4f}%"
                    + ("<br>ⓘ estimasi" if it.get("is_estimated") else "")
                    + (
                        f"<br>Harga: {it['price']:.4f}" if it.get("price") is not None else ""
                    )
                )
                for it in items
            ],
            hoverinfo="text",
            name=bond_code,
        )
    )
    base_layout(fig, height=380, x_title="Tanggal observasi", y_title="Yield (%)")
    fig.update_yaxes(tickformat=".2f")
    return fig


def inflation_fig(real_items: list[dict], dummy_items: list[dict]) -> go.Figure:
    """Inflation YoY: official series separated from dummy (RULES.md 3).

    The two sets are drawn as separate traces -- the gap between official data
    ending (e.g. 2023) and dummy (2026) is never bridged by a connecting line,
    and dummy is styled as a dashed neutral line, not mixed into the official
    statistic.
    """
    fig = go.Figure()
    if real_items:
        fig.add_trace(
            go.Scatter(
                x=[it.get("observation_date") for it in real_items],
                y=[it.get("value") for it in real_items],
                mode="lines+markers",
                connectgaps=False,
                line={"color": styling.LEDGER_GREEN, "width": 2},
                marker={"color": styling.LEDGER_GREEN, "size": 5},
                text=[f"{it.get('observation_date')}<br>Inflasi YoY: {it['value']:.2f}%" for it in real_items],
                hoverinfo="text",
                name="Resmi (BPS)",
            )
        )
    if dummy_items:
        fig.add_trace(
            go.Scatter(
                x=[it.get("observation_date") for it in dummy_items],
                y=[it.get("value") for it in dummy_items],
                mode="markers",
                connectgaps=False,
                line={"color": styling.INK_MUTED, "width": 2, "dash": "dot"},
                marker={
                    "color": styling.SURFACE,
                    "line": {"color": styling.INK_MUTED, "width": 2},
                    "size": 9,
                    "symbol": "diamond-open",
                },
                text=[f"{it.get('observation_date')}<br>Inflasi YoY (contoh): {it['value']:.2f}%" for it in dummy_items],
                hoverinfo="text",
                name="Contoh (DUMMY)",
            )
        )
    base_layout(fig, height=380, x_title="Bulan", y_title="Inflasi YoY (%)")
    fig.update_yaxes(tickformat=".2f")
    return fig


def step_rate_fig(items: list[dict], title_y: str) -> go.Figure:
    """Step chart for a policy rate that holds between announcements (bi_7drr).

    A plain line would read as 'missing data' between the sparse change dates;
    a step (hold-value) trace is the truthful representation for a rate that is
    constant until the next policy decision.
    """
    items = [it for it in items if it.get("value") is not None]
    xs = [it.get("observation_date") for it in items]
    ys = [it.get("value") for it in items]

    # Step needs duplicated points so matplotlib/plotly step 'hv' holds level.
    step_x: list = []
    step_y: list = []
    for i, (x, y) in enumerate(zip(xs, ys)):
        step_x.append(x)
        step_y.append(y)
        if i + 1 < len(xs):
            step_x.append(xs[i + 1])
            step_y.append(y)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=step_x,
            y=step_y,
            mode="lines",
            line={"shape": "hv", "color": styling.LEDGER_GREEN, "width": 2},
            customdata=[[it.get("source")] for it in items],
            hovertemplate="%{x}<br>BI7DRR: %{y:.2f}%<extra></extra>",
            name="BI7DRR",
        )
    )
    # Actual announcement points on top for precision.
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            marker={"color": styling.SURFACE, "line": {"color": styling.LEDGER_GREEN, "width": 2}, "size": 6},
            hovertemplate="%{x}<br>Besar perubahan (pengumuman)<extra></extra>",
            name="Titik pengumuman",
        )
    )
    base_layout(fig, height=380, x_title="Tanggal", y_title=f"{title_y} (%)")
    fig.update_yaxes(tickformat=".2f")
    return fig


def daily_series_fig(items: list[dict], title: str) -> go.Figure:
    """Daily series (e.g. JISDOR USD/IDR) -- gaps stay broken."""
    items = [it for it in items if it.get("value") is not None]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[it.get("observation_date") for it in items],
            y=[it.get("value") for it in items],
            mode="lines",
            connectgaps=False,
            line={"color": styling.LEDGER_GREEN, "width": 1.5},
            customdata=[[it.get("source")] for it in items],
            hovertemplate="%{x}<br>Kurs: %{y:,.2f}<extra></extra>",
            name=title,
        )
    )
    base_layout(fig, height=380, x_title="Tanggal", y_title=title)
    fig.update_yaxes(tickformat=",.2f")
    return fig
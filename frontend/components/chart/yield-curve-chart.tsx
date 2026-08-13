"use client";

/**
 * Hero chart: current government yield curve (x = tenor, y = yield).
 *
 * Client component (interactive tooltip + data freshness). Fetches
 * `/api/yield-curve/current` via lib/api-client on mount and renders a
 * ledger-green line with NO gradient fill (DESIGN.md §4). Loaded lazily from
 * the page with next/dynamic ssr:false (note in ARCHITECTURE.md / DESIGN.md:
 * charts stay isolated so they don't bloat first-load JS).
 */
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useEffect, useId, useState } from "react";

import { ApiClientError, getCurrentCurve, toNumber } from "@/lib/api-client";
import type { YieldCurvePoint } from "@/lib/api-client";

import { CHART, fmtDate, fmtYears, fmtYield } from "./chart-utils";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "./chart-ui";
import { downloadCsv } from "@/lib/csv-export";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty"; message?: string }
  | { kind: "ready"; points: CurvePoint[]; asOf: string | null };

interface CurvePoint {
  tenor: number | null;
  yieldValue: number | null;
  bondCode: string;
  bondName: string;
  couponRate: number | null;
  maturityDate: string | null;
  observationDate: string;
  source: string;
}

function toPoints(items: YieldCurvePoint[]): CurvePoint[] {
  return items
    .map((it) => ({
      tenor: toNumber(it.tenor_years),
      yieldValue: toNumber(it.yield_value),
      bondCode: it.bond_code,
      bondName: it.bond_name,
      couponRate: toNumber(it.coupon_rate),
      maturityDate: it.maturity_date,
      observationDate: it.observation_date,
      source: it.source,
    }))
    .sort((a, b) => {
      if (a.tenor === null && b.tenor === null) return 0;
      if (a.tenor === null) return 1;
      if (b.tenor === null) return -1;
      return a.tenor - b.tenor;
    });
}

export default function YieldCurveChart({
  ariaLabel = "Kurva yield obligasi pemerintah Indonesia",
}: {
  ariaLabel?: string;
}) {
  const chartId = useId();
  const [state, setState] = useState<State>({ kind: "loading" });
  const [tick, setTick] = useState(0);

  const load = () => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  };

  useEffect(() => {
    let cancelled = false;
    getCurrentCurve()
      .then((resp) => {
        if (cancelled) return;
        if (resp.status === "empty" || resp.items.length === 0) {
          setState({ kind: "empty" });
          return;
        }
        const points = toPoints(resp.items);
        if (points.every((p) => p.yieldValue === null)) {
          setState({ kind: "empty", message: "Yield tidak tersedia." });
          return;
        }
        setState({ kind: "ready", points, asOf: resp.as_of });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof ApiClientError
            ? err.message
            : "Terjadi kesalahan saat memuat data.";
        setState({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  const source = state.kind === "ready" ? state.points[0]?.source : null;

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = state.points.map((p) => ({
      kode_obligasi: p.bondCode,
      nama: p.bondName,
      tenor_tahun: p.tenor,
      yield: p.yieldValue,
      kupon: p.couponRate,
      jatuh_tempo: p.maturityDate,
      tanggal_observasi: p.observationDate,
      sumber: p.source,
    }));
    downloadCsv(rows, "obliq-kurva-yield");
  };

  return (
    <div>
      <div
        className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface"
        role="img"
        aria-label={ariaLabel}
      >
        {state.kind === "loading" ? (
          <div className="h-64 animate-pulse sm:h-72" aria-hidden="true">
            <svg className="h-full w-full" viewBox="0 0 600 200" preserveAspectRatio="none">
              <rect x="16" y="16" width="60" height="12" rx="6" className="fill-ink/10" />
              <rect x="16" y="120" width="12" height="64" className="fill-ink/10" />
              <rect x="584" y="120" width="0" height="0" className="fill-ink/10" />
              <path
                d="M 40 150 L 90 146 L 140 148 L 190 138 L 240 142 L 290 128 L 340 134 L 390 120 L 440 124 L 490 108 L 540 114 L 570 100"
                fill="none"
                stroke="#6B6355"
                strokeOpacity="0.35"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
              <line x1="40" y1="180" x2="570" y2="180" className="stroke-ink/15" strokeWidth="1" />
            </svg>
          </div>
        ) : state.kind === "error" ? (
          <ChartError message={state.message} onRetry={load} />
        ) : state.kind === "empty" ? (
          <ChartEmpty message="Data kurva yield tidak tersedia." />
        ) : (
          <ResponsiveContainer width="100%" height={288}>
            <LineChart
              data={state.points}
              margin={{ top: 16, right: 24, bottom: 8, left: 8 }}
            >
              <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="tenor"
                type="number"
                domain={["dataMin", "dataMax"]}
                tickFormatter={(v: number) => fmtYears(v)}
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={{ stroke: CHART.axis }}
                tickLine={false}
                label={{ value: "Tenor (th)", position: "insideBottom", offset: -2, fill: CHART.inkMuted, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
              />
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(v: number) => fmtYield(v, 1)}
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={false}
                tickLine={false}
                width={48}
                label={{ value: "Yield (%)", angle: -90, position: "insideLeft", offset: 4, fill: CHART.inkMuted, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
              />
              <Tooltip
                cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }}
                offset={-26}
                content={<CurveTooltip />}
              />
              <Line
                dataKey="yieldValue"
                type="monotone"
                stroke={CHART.ledgerGreen}
                strokeWidth={2}
                dot={{ r: 2.5, fill: CHART.ledgerGreen, strokeWidth: 0 }}
                activeDot={{ r: 4 }}
                connectNulls={false}
                isAnimationActive={false}
                name={`Kurva yield (${chartId})`}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {state.kind === "ready" && (
        <ChartCaption source={source ?? "DJPPR"} date={fmtDate(state.asOf)}>
          <CsvButton onClick={handleCsv} />
        </ChartCaption>
      )}
    </div>
  );
}

function CurveTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: CurvePoint }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">
        {p.bondCode} — {p.bondName}
      </p>
      <TooltipRow label="Tenor" value={fmtYears(p.tenor)} />
      <TooltipRow label="Yield" value={fmtYield(p.yieldValue)} />
      <TooltipRow label="Kupon" value={fmtYield(p.couponRate)} />
      <TooltipRow label="Jatuh tempo" value={p.maturityDate ? fmtDate(p.maturityDate) : "—"} />
      <TooltipRow label="Observasi" value={fmtDate(p.observationDate)} />
      <TooltipRow label="Sumber" value={p.source} />
    </ChartTooltip>
  );
}
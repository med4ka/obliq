"use client";

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

import { ApiClientError, getStockHistory, toNumber } from "@/lib/api-client";
import type { StockObservationItem } from "@/lib/api-client";

import { CHART, fmtDate, fmtDateShort, fmtNumber } from "./chart-utils";
import { downloadCsv } from "@/lib/csv-export";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "./chart-ui";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty"; message?: string }
  | { kind: "ready"; points: StockPoint[]; source: string; date: string };

interface StockPoint {
  t: number;
  close: number | null;
  date: string;
}

const MAX_GAP_DAYS = 45;

export default function StockChart({
  ticker,
}: {
  ticker: string;
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
    getStockHistory(ticker)
      .then((resp) => {
        if (cancelled) return;
        if (resp.status === "empty" || resp.items.length === 0) {
          setState({ kind: "empty" });
          return;
        }
        const points = toPoints(resp.items);
        if (points.every((p) => p.close === null)) {
          setState({ kind: "empty", message: `Data ${ticker} tidak tersedia.` });
          return;
        }
        const last = resp.items[resp.items.length - 1];
        setState({
          kind: "ready",
          points,
          source: last.source,
          date: last.observation_date,
        });
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
  }, [tick, ticker]);

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = state.points.map((p) => ({
      tanggal: p.date,
      close: p.close,
    }));
    downloadCsv(rows, `obliq-${ticker}`);
  };

  return (
    <div>
      <div
        className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface"
        role="img"
        aria-label={`${ticker} historis`}
      >
        {state.kind === "loading" ? (
          <div className="h-64 animate-pulse sm:h-72" aria-hidden="true">
            <svg className="h-full w-full" viewBox="0 0 600 200" preserveAspectRatio="none">
              <rect x="16" y="16" width="60" height="12" rx="6" className="fill-ink/10" />
              <rect x="16" y="120" width="12" height="64" className="fill-ink/10" />
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
          <ChartEmpty message={`Data ${ticker} tidak tersedia.`} />
        ) : (
          <ResponsiveContainer width="100%" height={288}>
            <LineChart
              data={state.points}
              margin={{ top: 16, right: 24, bottom: 8, left: 8 }}
            >
              <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="t"
                type="number"
                domain={["dataMin", "dataMax"]}
                interval="preserveStartEnd"
                minTickGap={50}
                tickFormatter={(v: number) => fmtDateShort(new Date(v).toISOString().slice(0, 10))}
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={{ stroke: CHART.axis }}
                tickLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(v: number) => fmtNumber(v)}
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={false}
                tickLine={false}
                width={56}
              />
              <Tooltip
                cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }}
                offset={-26}
                content={<StockTooltip />}
              />
              <Line
                dataKey="close"
                type="monotone"
                stroke={CHART.ledgerGreen}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls={false}
                isAnimationActive={false}
                name={`${ticker} (${chartId})`}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {state.kind === "ready" && (
        <ChartCaption source={state.source} date={fmtDate(state.date)}>
          <CsvButton onClick={handleCsv} />
        </ChartCaption>
      )}
    </div>
  );
}

function toPoints(items: StockObservationItem[]): StockPoint[] {
  const out: StockPoint[] = [];
  for (let i = 0; i < items.length; i++) {
    const prev = items[i - 1];
    const cur = items[i];
    const curT = new Date(`${cur.observation_date}T00:00:00`).getTime();
    if (prev) {
      const prevT = new Date(`${prev.observation_date}T00:00:00`).getTime();
      const gap = (curT - prevT) / 86_400_000;
      if (gap > MAX_GAP_DAYS) {
        out.push({ t: (prevT + curT) / 2, close: null, date: "" });
      }
    }
    out.push({
      t: curT,
      close: toNumber(cur.close),
      date: cur.observation_date,
    });
  }
  return out;
}

function StockTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: StockPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (p.close === null) return null;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{fmtDate(p.date)}</p>
      <TooltipRow label="Close" value={fmtNumber(p.close)} />
    </ChartTooltip>
  );
}

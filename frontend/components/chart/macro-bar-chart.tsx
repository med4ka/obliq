"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useEffect, useState } from "react";

import { ApiClientError, getMacroHistory, toNumber } from "@/lib/api-client";
import type { MacroItem } from "@/lib/api-client";

import { CHART, fmtDate, fmtNumber, fmtYield } from "./chart-utils";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "./chart-ui";
import { downloadCsv } from "@/lib/csv-export";

export interface MacroBarChartProps {
  indicatorType: string;
  title: string;
  unit: "usd" | "pct";
  ariaLabel?: string;
}

type BarPoint = {
  label: string;
  value: number | null;
  date: string;
  rawDate: string;
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; points: BarPoint[]; source: string; date: string };

export default function MacroBarChart({
  indicatorType,
  title,
  unit,
  ariaLabel,
}: MacroBarChartProps) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [tick, setTick] = useState(0);

  const load = () => {
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  };

  useEffect(() => {
    let cancelled = false;
    getMacroHistory(indicatorType)
      .then((resp) => {
        if (cancelled) return;
        if (resp.status === "empty" || resp.items.length === 0) {
          setState({ kind: "empty" });
          return;
        }
        const points: BarPoint[] = resp.items.map((it: MacroItem) => {
          const val = toNumber(it.value);
          const d = new Date(`${it.observation_date}T00:00:00`);
          const month = d.toLocaleString("id-ID", { month: "short" });
          const year = d.getFullYear();
          const isQuarter =
            d.getMonth() === 2 || d.getMonth() === 5 || d.getMonth() === 8 || d.getMonth() === 11;
          const label = isQuarter
            ? `Q${Math.floor(d.getMonth() / 3) + 1} ${year}`
            : `${month} ${year}`;
          return {
            label,
            value: val,
            date: fmtDate(it.observation_date),
            rawDate: it.observation_date,
          };
        });
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
  }, [indicatorType, tick]);

  const label = ariaLabel ?? title;

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = state.points.map((p) => ({
      tanggal: p.rawDate,
      label: p.label,
      nilai: p.value,
    }));
    downloadCsv(rows, `obliq-makro-${indicatorType}`);
  };

  return (
    <div>
      <div
        className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface"
        role="img"
        aria-label={label}
      >
        {state.kind === "loading" ? (
          <div className="h-56 animate-pulse sm:h-64" aria-hidden="true">
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
          <ChartEmpty message={`Data ${title} tidak tersedia.`} />
        ) : (
          <ResponsiveContainer width="100%" height={256}>
            <BarChart data={state.points} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
              <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="label"
                interval="preserveStartEnd"
                minTickGap={40}
                tick={{ fill: CHART.axis, fontSize: 10, fontFamily: "var(--font-plex-mono)" }}
                axisLine={{ stroke: CHART.axis }}
                tickLine={false}
              />
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(v: number) =>
                  unit === "usd" ? fmtNumber(v) : fmtYield(v, 1)
                }
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={false}
                tickLine={false}
                width={56}
              />
              <Tooltip
                cursor={{ fill: CHART.grid }}
                offset={-26}
                content={<BarTooltip title={title} unit={unit} />}
              />
              <ReferenceLine y={0} stroke={CHART.axis} strokeWidth={1} />
              <Bar
                dataKey="value"
                fill={CHART.ledgerGreen}
                radius={[2, 2, 0, 0]}
                isAnimationActive={false}
              />
            </BarChart>
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

function BarTooltip({
  active,
  payload,
  title,
  unit,
}: {
  active?: boolean;
  payload?: { payload: BarPoint }[];
  title: string;
  unit: "usd" | "pct";
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (p.value === null) return null;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{p.date}</p>
      <TooltipRow
        label={title}
        value={
          unit === "usd"
            ? `USD ${fmtNumber(p.value)}`
            : fmtYield(p.value)
        }
      />
    </ChartTooltip>
  );
}

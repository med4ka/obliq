"use client";

/**
 * Reusable macro indicator chart (used 3x on /makro).
 *
 * - inflation: official BPS line (ledger-green) with dummy rows kept in a
 *   SEPARATE dashed neutral trace + DUMMY badge (RULES.md §3, decision from the
 *   old Streamlit dashboard): the 2024-2025 hole between real and dummy data
 *   stays visibly broken, never bridged.
 * - bi_7drr: step chart (`type="stepAfter"`) — a policy rate holds its value
 *   until the next decision, so a stepped line is the truthful shape.
 * - usd_idr: daily line with broken gaps.
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
import { useEffect, useState } from "react";

import { ApiClientError, getMacroHistory } from "@/lib/api-client";
import type { MacroItem } from "@/lib/api-client";

import { CHART, fmtDate, fmtDateShort, fmtNumber, fmtYield, toTimePoints } from "./chart-utils";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  DummyBadge,
  TooltipRow,
} from "./chart-ui";
import { downloadCsv } from "@/lib/csv-export";

export type MacroVariant = "inflation" | "step" | "daily" | "sparse";

export interface MacroChartProps {
  indicatorType: string;
  title: string;
  variant: MacroVariant;
  ariaLabel?: string;
}

type MacroPoint = {
  t: number;
  y: number | null;
  isDummy: boolean;
  date: string;
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | { kind: "ready"; points: MacroPoint[]; source: string; date: string };

const MAX_GAP_DAYS: Record<MacroVariant, number> = {
  inflation: 120, // monthly series: >4 months hole = real gap
  step: 180, // policy rate: decisions are weeks-to-months apart
  daily: 21, // JISDOR: ~3 weeks without a fixing = broken line
  sparse: 400, // annual: data points up to a year apart -> no false gaps
};

export default function MacroChart({
  indicatorType,
  title,
  variant,
  ariaLabel,
}: MacroChartProps) {
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
        const raw = toTimePoints(
          resp.items.map((it: MacroItem) => ({
            date: it.observation_date,
            value: it.value,
          })),
          MAX_GAP_DAYS[variant]
        );
        const byTime = new Map<number, MacroItem>();
        for (const it of resp.items) {
          byTime.set(new Date(`${it.observation_date}T00:00:00`).getTime(), it);
        }
        const points: MacroPoint[] = raw.map((pt) => {
          const item = byTime.get(pt.t);
          return {
            t: pt.t,
            y: pt.y,
            isDummy: item?.is_dummy ?? false,
            date: item?.observation_date ?? new Date(pt.t).toISOString().slice(0, 10),
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
  }, [indicatorType, variant, tick]);

  const hasDummy =
    state.kind === "ready" && state.points.some((p) => p.isDummy);
  const label = ariaLabel ?? title;

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = state.points.map((p) => ({
      tanggal: p.date,
      nilai: p.y,
      is_dummy: p.isDummy,
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
            <LineChart data={state.points} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
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
                tickFormatter={(v: number) =>
                  variant === "daily" ? fmtNumber(v) : fmtYield(v, 1)
                }
                tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip
                cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }}
                offset={-26}
                content={<MacroTooltip variant={variant} title={title} />}
              />
              {variant === "inflation" ? (
                <>
                  <Line
                    dataKey="y"
                    type="monotone"
                    stroke={CHART.ledgerGreen}
                    strokeWidth={2}
                    dot={{ r: 2.5, fill: CHART.ledgerGreen, strokeWidth: 0 }}
                    activeDot={{ r: 4 }}
                    connectNulls={false}
                    isAnimationActive={false}
                    name="Resmi"
                    data={state.points.filter((p) => !p.isDummy)}
                  />
                  <Line
                    dataKey="y"
                    type="monotone"
                    stroke={CHART.inkMuted}
                    strokeDasharray="5 4"
                    strokeWidth={1.5}
                    dot={{ r: 3, fill: CHART.surface, stroke: CHART.inkMuted, strokeWidth: 1.5 }}
                    activeDot={{ r: 4 }}
                    connectNulls={false}
                    isAnimationActive={false}
                    name="Contoh (DUMMY)"
                    data={state.points.filter((p) => p.isDummy)}
                  />
                </>
              ) : (
                <Line
                  dataKey="y"
                  type={variant === "step" ? "stepAfter" : "monotone"}
                  stroke={CHART.ledgerGreen}
                  strokeWidth={variant === "sparse" ? 2 : variant === "daily" ? 1.5 : 2}
                  dot={
                    variant === "step"
                      ? { r: 3, fill: CHART.surface, stroke: CHART.ledgerGreen, strokeWidth: 1.5 }
                      : variant === "sparse"
                        ? { r: 4, fill: CHART.ledgerGreen, strokeWidth: 0 }
                        : { r: 1, fill: CHART.ledgerGreen, strokeWidth: 0 }
                  }
                  activeDot={{ r: 4 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {state.kind === "ready" && (
        <ChartCaption source={state.source} date={fmtDate(state.date)}>
          {hasDummy ? <DummyBadge /> : null}
          <CsvButton onClick={handleCsv} />
        </ChartCaption>
      )}
    </div>
  );
}

function MacroTooltip({
  active,
  payload,
  variant,
  title,
}: {
  active?: boolean;
  payload?: { payload: MacroPoint }[];
  variant: MacroVariant;
  title: string;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (p.y === null) return null;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{fmtDate(p.date)}</p>
      <TooltipRow
        label={title}
        value={variant === "daily" ? fmtNumber(p.y) : fmtYield(p.y)}
      />
      {p.isDummy ? (
        <p className="mt-1 font-serif text-[11px] font-semibold text-seal-red">
          DATA CONTOH — BELUM DARI SUMBER RESMI
        </p>
      ) : null}
    </ChartTooltip>
  );
}
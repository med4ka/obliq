"use client";

/**
 * "Histori Yield Satu Seri": pick a bond code, show its yield over time.
 *
 * Gaps (ARCHITECTURE.md §4): `connectNulls={false}` plus an explicit null
 * point inserted at the midpoint of any date range > MAX_GAP_DAYS so a long
 * hole in the data reads as a broken line, never a silently-drawn bridge.
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

import {
  ApiClientError,
  getBondHistory,
} from "@/lib/api-client";
import type { YieldHistoryItem } from "@/lib/api-client";

import {
  CHART,
  fmtDate,
  fmtDateShort,
  fmtYield,
  toTimePoints,
  type TimePoint,
} from "./chart-utils";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "./chart-ui";
import { downloadCsv } from "@/lib/csv-export";

const MAX_GAP_DAYS = 90;

interface HistoryPoint extends TimePoint {
  source?: string;
}

interface HistoryMeta {
  bondCode: string;
  bondName: string | null;
  source: string;
  date: string;
}

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "empty" }
  | {
      kind: "ready";
      points: HistoryPoint[];
      meta: HistoryMeta;
    };

export default function YieldHistoryChart({
  defaultBondCode = "FR0100",
}: {
  defaultBondCode?: string;
}) {
  const [bondCode, setBondCode] = useState(defaultBondCode);
  const [submitted, setSubmitted] = useState(defaultBondCode);
  const [state, setState] = useState<State>({ kind: "loading" });
  const [tick, setTick] = useState(0);

  const load = (code: string) => {
    setSubmitted(code);
    setState({ kind: "loading" });
    setTick((t) => t + 1);
  };

  useEffect(() => {
    let cancelled = false;
    getBondHistory(submitted)
      .then((resp) => {
        if (cancelled) return;
        if (resp.status === "not_found") {
          setState({
            kind: "error",
            message: `Seri "${submitted}" tidak ditemukan di basis data.`,
          });
          return;
        }
        if (resp.status === "empty" || resp.items.length === 0) {
          setState({ kind: "empty" });
          return;
        }
        const points = toTimePoints(
          resp.items.map((it: YieldHistoryItem) => ({
            date: it.observation_date,
            value: it.yield_value,
          })),
          MAX_GAP_DAYS
        ) as HistoryPoint[];
        const sourceByTime = new Map<number, string>();
        for (const it of resp.items) {
          const ts = new Date(`${it.observation_date}T00:00:00`).getTime();
          sourceByTime.set(ts, it.source);
        }
        for (const pt of points) {
          if (pt.y !== null) pt.source = sourceByTime.get(pt.t) ?? undefined;
        }
        const last = resp.items[resp.items.length - 1];
        setState({
          kind: "ready",
          points,
          meta: {
            bondCode: resp.bond_code,
            bondName: resp.bond_name,
            source: last.source,
            date: last.observation_date,
          },
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const message =
          err instanceof ApiClientError
            ? err.message
            : "Terjadi kesalahan saat memuat histori.";
        setState({ kind: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [submitted, tick]);

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = state.points.map((p) => ({
      tanggal: new Date(p.t).toISOString().slice(0, 10),
      yield: p.y,
      sumber: p.source ?? "",
    }));
    downloadCsv(rows, `obliq-histori-${submitted}`);
  };

  return (
    <div>
      <form
        className="mb-4 flex flex-wrap items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const code = bondCode.trim().toUpperCase();
          if (code) load(code);
        }}
      >
        <label className="flex flex-col gap-1 font-mono text-xs text-ink-muted">
          Kode seri
          <input
            type="text"
            value={bondCode}
            onChange={(e) => setBondCode(e.target.value)}
            placeholder="mis. FR0100"
            className="w-36 rounded-md border border-ink/20 bg-surface px-2.5 py-1.5 font-mono text-sm text-ink outline-none transition-colors focus:border-ledger-green"
            aria-label="Kode seri obligasi"
          />
        </label>
        <button
          type="submit"
          className="rounded-md border border-ledger-green bg-ledger-green px-3 py-1.5 font-mono text-xs text-parchment transition-colors hover:bg-ledger-green/90"
        >
          Tampilkan
        </button>
      </form>

      <div
        className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface"
        role="img"
        aria-label={`Histori yield seri ${submitted}`}
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
          <ChartError message={state.message} onRetry={() => load(submitted)} />
        ) : state.kind === "empty" ? (
          <ChartEmpty message={`Belum ada data histori untuk seri ${submitted}.`} />
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
                label={{ value: "Tanggal observasi", position: "insideBottom", offset: -2, fill: CHART.inkMuted, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
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
                content={<HistoryTooltip />}
              />
              <Line
                dataKey="y"
                type="monotone"
                stroke={CHART.ledgerGreen}
                strokeWidth={2}
                dot={{ r: 2.5, fill: CHART.ledgerGreen, strokeWidth: 0 }}
                activeDot={{ r: 4 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {state.kind === "ready" && (
        <ChartCaption
          source={state.meta.source}
          date={fmtDate(state.meta.date)}
        >
          {state.meta.bondName ? (
            <span className="font-mono text-xs text-ink-muted">{state.meta.bondName}</span>
          ) : null}
          <CsvButton onClick={handleCsv} />
        </ChartCaption>
      )}
    </div>
  );
}

function HistoryTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: HistoryPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  if (p.y === null) return null;
  const date = fmtDate(new Date(p.t).toISOString().slice(0, 10));
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{date}</p>
      <TooltipRow label="Yield" value={fmtYield(p.y)} />
      {p.source ? <TooltipRow label="Sumber" value={p.source} /> : null}
    </ChartTooltip>
  );
}
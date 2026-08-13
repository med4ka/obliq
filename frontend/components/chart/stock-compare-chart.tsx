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
import { useEffect, useMemo, useState } from "react";

import { ApiClientError, getStockHistory, toNumber } from "@/lib/api-client";

import { CHART, fmtDate, fmtDateShort, fmtNumber } from "./chart-utils";
import {
  ChartCaption,
  ChartEmpty,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "./chart-ui";
import { downloadCsv } from "@/lib/csv-export";

const COLORS = [CHART.ledgerGreen, CHART.gold, CHART.ink] as const;

interface Series {
  ticker: string;
  points: { t: number; close: number | null }[];
  source: string;
  date: string;
}

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; series: Series[] };

export default function StockCompareChart({ tickers }: { tickers: string[] }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      tickers.map(async (t) => {
        const resp = await getStockHistory(t);
        if (resp.status !== "ok" || resp.items.length === 0) return null;
        const points = resp.items.map((r) => ({
          t: new Date(`${r.observation_date}T00:00:00`).getTime(),
          close: toNumber(r.close),
        }));
        const last = resp.items[resp.items.length - 1];
        return { ticker: t, points, source: last.source, date: last.observation_date } as Series;
      })
    ).then((results) => {
      if (cancelled) return;
      const series = results.filter((r): r is Series => r !== null);
      if (series.length === 0) {
        setState({ kind: "error", message: "Tidak ada data saham yang dipilih." });
        return;
      }
      setState({ kind: "ready", series });
    }).catch((err: unknown) => {
      if (cancelled) return;
      setState({ kind: "error", message: err instanceof ApiClientError ? err.message : "Gagal memuat data." });
    });
    return () => { cancelled = true; };
  }, [tickers]);

  const merged = useMemo(() => {
    if (state.kind !== "ready") return [];
    const allTs = new Set<number>();
    state.series.forEach((s) => s.points.forEach((p) => allTs.add(p.t)));
    return Array.from(allTs).sort((a, b) => a - b).map((t) => {
      const row: Record<string, number | null> = { t };
      state.series.forEach((s) => {
        const found = s.points.find((p) => p.t === t);
        row[s.ticker] = found ? found.close : null;
      });
      return row;
    });
  }, [state]);

  if (state.kind === "loading") {
    return (
      <div className="h-64 animate-pulse sm:h-72" aria-hidden="true">
        <svg className="h-full w-full" viewBox="0 0 600 200" preserveAspectRatio="none">
          <rect x="16" y="16" width="80" height="12" rx="6" className="fill-ink/10" />
          <rect x="16" y="36" width="60" height="12" rx="6" className="fill-ink/10" />
          <path d="M 40 150 L 90 146 L 140 148 L 190 138 L 240 142 L 290 128 L 340 134 L 390 120 L 440 124 L 490 108 L 540 114 L 570 100" fill="none" stroke="#6B6355" strokeOpacity="0.35" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          <line x1="40" y1="180" x2="570" y2="180" className="stroke-ink/15" strokeWidth="1" />
        </svg>
      </div>
    );
  }

  if (state.kind === "error") {
    return <ChartError message={state.message} />;
  }

  if (state.series.length < 2) {
    return <ChartEmpty message="Pilih minimal 2 saham untuk dibandingkan." />;
  }

  const allDates = state.series.map((s) => s.date);
  const latestDate = allDates.sort()[allDates.length - 1];
  const sources = [...new Set(state.series.map((s) => s.source))].join(", ");

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = merged.map((r) => {
      const row: Record<string, string | number | null> = {
        tanggal: new Date(r.t as number).toISOString().slice(0, 10),
      };
      state.series.forEach((s) => { row[s.ticker] = r[s.ticker]; });
      return row;
    });
    downloadCsv(rows, "obliq-banding-saham");
  };

  return (
    <div>
      <div className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={merged} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
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
              width={60}
            />
            <Tooltip
              cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }}
              offset={-26}
              content={<CompareTooltip tickers={tickers} />}
            />
            {state.series.map((s, i) => (
              <Line
                key={s.ticker}
                dataKey={s.ticker}
                type="monotone"
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls={false}
                isAnimationActive={false}
                name={s.ticker}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
        {state.series.map((s, i) => (
          <span key={s.ticker} className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
            <span className="text-ink-muted">{s.ticker}</span>
          </span>
        ))}
      </div>

      <ChartCaption source={sources} date={fmtDate(latestDate)}>
        <CsvButton onClick={handleCsv} />
      </ChartCaption>
    </div>
  );
}

function CompareTooltip({ active, payload, tickers }: { active?: boolean; payload?: { dataKey: string | number; value: number; payload: Record<string, unknown> }[]; tickers: string[] }) {
  if (!active || !payload?.length) return null;
  const t = payload[0]?.payload?.t as number | undefined;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{t ? fmtDate(new Date(t).toISOString().slice(0, 10)) : ""}</p>
      {tickers.map((tik) => {
        const p = payload.find((pp) => String(pp.dataKey) === tik);
        return p ? <TooltipRow key={tik} label={tik} value={fmtNumber(p.value)} /> : null;
      })}
    </ChartTooltip>
  );
}

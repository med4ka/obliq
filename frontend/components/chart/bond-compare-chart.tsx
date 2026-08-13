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

import { ApiClientError, getBondHistory } from "@/lib/api-client";

import { CHART, fmtDate, fmtDateShort, fmtYield, toTimePoints } from "./chart-utils";
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
  code: string;
  points: { t: number; y: number | null }[];
  source: string;
  date: string;
}

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; series: Series[] };

const MAX_GAP = 90;

export default function BondCompareChart({ codes }: { codes: string[] }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      codes.map(async (code) => {
        const resp = await getBondHistory(code);
        if (resp.status !== "ok" || resp.items.length === 0) return null;
        const points = toTimePoints(
          resp.items.map((it) => ({ date: it.observation_date, value: it.yield_value })),
          MAX_GAP
        );
        const last = resp.items[resp.items.length - 1];
        return { code, points, source: last.source, date: last.observation_date } as Series;
      })
    ).then((results) => {
      if (cancelled) return;
      const series = results.filter((r): r is Series => r !== null);
      if (series.length === 0) {
        setState({ kind: "error", message: "Tidak ada data obligasi yang dipilih." });
        return;
      }
      setState({ kind: "ready", series });
    }).catch((err: unknown) => {
      if (cancelled) return;
      setState({ kind: "error", message: err instanceof ApiClientError ? err.message : "Gagal memuat data." });
    });
    return () => { cancelled = true; };
  }, [codes]);

  const merged = useMemo(() => {
    if (state.kind !== "ready") return [];
    const allTs = new Set<number>();
    state.series.forEach((s) => s.points.forEach((p) => allTs.add(p.t)));
    return Array.from(allTs).sort((a, b) => a - b).map((t) => {
      const row: Record<string, number | null> = { t };
      state.series.forEach((s) => {
        const found = s.points.find((p) => p.t === t);
        row[s.code] = found ? found.y : null;
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
          <path d="M 40 150 L 90 146 L 140 148 L 190 138 L 240 142 L 290 128 L 340 134 L 390 120 L 440 124 L 490 108 L 540 114 L 570 100" fill="none" stroke="#6B6355" strokeOpacity="0.35" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          <line x1="40" y1="180" x2="570" y2="180" className="stroke-ink/15" strokeWidth="1" />
        </svg>
      </div>
    );
  }

  if (state.kind === "error") return <ChartError message={state.message} />;
  if (state.series.length < 2) return <ChartEmpty message="Pilih minimal 2 seri obligasi untuk dibandingkan." />;

  const latestDate = state.series.map((s) => s.date).sort()[state.series.length - 1];
  const sources = [...new Set(state.series.map((s) => s.source))].join(", ");

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = merged.map((r) => {
      const row: Record<string, string | number | null> = {
        tanggal: new Date(r.t as number).toISOString().slice(0, 10),
      };
      state.series.forEach((s) => { row[s.code] = r[s.code]; });
      return row;
    });
    downloadCsv(rows, "obliq-banding-obligasi");
  };

  return (
    <div>
      <div className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface">
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={merged} margin={{ top: 16, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="t" type="number" domain={["dataMin", "dataMax"]}
              interval="preserveStartEnd" minTickGap={50}
              tickFormatter={(v: number) => fmtDateShort(new Date(v).toISOString().slice(0, 10))}
              tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
              axisLine={{ stroke: CHART.axis }} tickLine={false}
            />
            <YAxis
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => fmtYield(v, 1)}
              tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
              axisLine={false} tickLine={false} width={52}
            />
            <Tooltip
              cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }}
              offset={-26}
              content={<BondTooltip codes={codes} />}
            />
            {state.series.map((s, i) => (
              <Line
                key={s.code}
                dataKey={s.code}
                type="monotone"
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3 }}
                connectNulls={false}
                isAnimationActive={false}
                name={s.code}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs">
        {state.series.map((s, i) => (
          <span key={s.code} className="inline-flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
            <span className="text-ink-muted">{s.code}</span>
          </span>
        ))}
      </div>
      <ChartCaption source={sources} date={fmtDate(latestDate)}>
        <CsvButton onClick={handleCsv} />
      </ChartCaption>
    </div>
  );
}

function BondTooltip({ active, payload, codes }: { active?: boolean; payload?: { dataKey: string | number; value: number; payload: Record<string, unknown> }[]; codes: string[] }) {
  if (!active || !payload?.length) return null;
  const t = payload[0]?.payload?.t as number | undefined;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{t ? fmtDate(new Date(t).toISOString().slice(0, 10)) : ""}</p>
      {codes.map((c) => {
        const p = payload.find((pp) => String(pp.dataKey) === c);
        return p ? <TooltipRow key={c} label={c} value={fmtYield(p.value)} /> : null;
      })}
    </ChartTooltip>
  );
}

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
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getBondHistory,
  getMacroHistory,
  getStockHistory,
  toNumber,
} from "@/lib/api-client";
import { CHART, fmtDate, fmtDateShort, fmtNumber } from "@/components/chart/chart-utils";
import {
  ChartCaption,
  ChartError,
  ChartTooltip,
  CsvButton,
  TooltipRow,
} from "@/components/chart/chart-ui";
import { downloadCsv } from "@/lib/csv-export";

const MACRO_OPTIONS: { type: string; label: string }[] = [
  { type: "inflation_yoy", label: "Inflasi (YoY)" },
  { type: "bi_7drr", label: "BI 7-Day RR" },
  { type: "usd_idr", label: "Kurs USD/IDR" },
  { type: "pdb_yoy", label: "PDB Growth" },
  { type: "trade_balance", label: "Neraca Perdagangan" },
  { type: "tpt", label: "TPT" },
  { type: "foreign_reserves", label: "Cadangan Devisa" },
];

interface SeriesItem {
  id: string;
  label: string;
  data: { t: number; v: number | null }[];
  source: string;
  unit: "pct" | "number";
}

type FetchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; series: SeriesItem[] };

function normalize(points: { t: number; v: number | null }[]): { t: number; v: number | null }[] {
  const first = points.find((p) => p.v !== null);
  if (!first?.v || first.v === 0) return points;
  const base = first.v;
  return points.map((p) => ({ t: p.t, v: p.v !== null ? (p.v / base) * 100 : null }));
}

export default function ComparePage() {
  const [bondCodes, setBondCodes] = useState("");
  const [stockTickers, setStockTickers] = useState("");
  const [macroSelected, setMacroSelected] = useState<string[]>([]);
  const [state, setState] = useState<FetchState>({ kind: "idle" });
  const [tick, setTick] = useState(0);

  const run = useCallback(() => {
    const bonds = bondCodes.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
    const stocks = stockTickers.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
    const macros = macroSelected;
    if (!bonds.length && !stocks.length && !macros.length) return;

    setState({ kind: "loading" });
    setTick((t) => t + 1);
  }, [bondCodes, stockTickers, macroSelected]);

  useEffect(() => {
    if (state.kind !== "loading") return;
    let cancelled = false;

    const bonds = bondCodes.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
    const stocks = stockTickers.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
    const macros = macroSelected;

    const fetchAll = async () => {
      const series: SeriesItem[] = [];

      for (const code of bonds) {
        try {
          const resp = await getBondHistory(code);
          if (resp.status === "empty" || resp.items.length === 0) continue;
          const pts = resp.items.map((it) => ({
            t: new Date(`${it.observation_date}T00:00:00`).getTime(),
            v: toNumber(it.yield_value),
          }));
          series.push({ id: code, label: code, data: pts, source: resp.items[0]?.source ?? "", unit: "pct" });
        } catch { /* skip */ }
      }

      for (const tik of stocks) {
        try {
          const resp = await getStockHistory(tik);
          if (resp.status === "empty" || resp.items.length === 0) continue;
          const pts = resp.items.map((it) => ({
            t: new Date(`${it.observation_date}T00:00:00`).getTime(),
            v: toNumber(it.close),
          }));
          series.push({ id: tik, label: tik, data: pts, source: resp.items[0]?.source ?? "", unit: "number" });
        } catch { /* skip */ }
      }

      for (const mt of macros) {
        try {
          const resp = await getMacroHistory(mt);
          if (resp.status === "empty" || resp.items.length === 0) continue;
          const pts = resp.items.map((it) => ({
            t: new Date(`${it.observation_date}T00:00:00`).getTime(),
            v: toNumber(it.value),
          }));
          const label = MACRO_OPTIONS.find((o) => o.type === mt)?.label ?? mt;
          series.push({ id: mt, label, data: pts, source: resp.items[0]?.source ?? "", unit: "pct" });
        } catch { /* skip */ }
      }

      if (cancelled) return;
      if (!series.length) {
        setState({ kind: "error", message: "Tidak ada data ditemukan untuk pilihan di atas." });
        return;
      }
      setState({ kind: "ready", series });
    };

    fetchAll();
    return () => { cancelled = true; };
  }, [state.kind === "loading" ? tick : -1]); // eslint-disable-line react-hooks/exhaustive-deps

  const normalized = useMemo(() => {
    if (state.kind !== "ready") return [];
    return state.series.map((s) => ({
      ...s,
      data: normalize(s.data),
    }));
  }, [state]);

  const merged = useMemo(() => {
    if (!normalized.length) return [];
    const allTs = new Set<number>();
    normalized.forEach((s) => s.data.forEach((p) => allTs.add(p.t)));
    return Array.from(allTs).sort((a, b) => a - b).map((t) => {
      const row: Record<string, number | null> = { t };
      normalized.forEach((s) => {
        const found = s.data.find((p) => p.t === t);
        row[s.id] = found ? found.v : null;
      });
      return row;
    });
  }, [normalized]);

  const colors = [CHART.ledgerGreen, CHART.gold, "#2563EB", "#DC2626", "#7C3AED", "#0891B2", "#D97706", "#059669"];

  const handleCsv = () => {
    if (state.kind !== "ready") return;
    const rows = merged.map((r) => {
      const row: Record<string, string | number | null> = {
        tanggal: new Date(r.t as number).toISOString().slice(0, 10),
      };
      state.series.forEach((s) => { row[s.label] = r[s.id]; });
      return row;
    });
    downloadCsv(rows, "obliq-perbandingan");
  };

  const latestDate = state.kind === "ready"
    ? state.series.map((s) => s.data.length ? new Date(s.data[s.data.length - 1].t).toISOString().slice(0, 10) : "").filter(Boolean).sort().pop() ?? null
    : null;
  const sources = state.kind === "ready" ? [...new Set(state.series.map((s) => s.source))].join(", ") : "";

  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-12 lg:px-8">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-muted">Perbandingan Lintas Kategori</p>
      <h1 className="mt-2 font-serif text-2xl font-semibold text-ink sm:text-3xl lg:text-4xl">
        Bandingkan Obligasi, Saham &amp; Makro
      </h1>
      <p className="mt-3 max-w-2xl text-sm text-ink-muted sm:text-base">
        Bandingkan pergerakan yield obligasi, harga saham, dan indikator makro
        dalam satu grafik. Semua seri dinormalisasi ke <strong>base 100</strong>{" "}
        (nilai awal masing-masing = 100) sehingga perbandingan perubahan relatif
        menjadi apple-to-apple meskipun satuan aslinya berbeda.
      </p>

      <form
        className="mt-6 grid gap-4 sm:grid-cols-3"
        onSubmit={(e) => { e.preventDefault(); run(); }}
      >
        <label className="flex flex-col gap-1 font-mono text-xs text-ink-muted">
          Kode seri obligasi
          <input
            type="text" value={bondCodes} onChange={(e) => setBondCodes(e.target.value)}
            placeholder="FR0100, FR0101"
            className="rounded-md border border-ink/20 bg-surface px-2.5 py-1.5 font-mono text-sm text-ink outline-none focus:border-ledger-green"
          />
        </label>
        <label className="flex flex-col gap-1 font-mono text-xs text-ink-muted">
          Kode saham
          <input
            type="text" value={stockTickers} onChange={(e) => setStockTickers(e.target.value)}
            placeholder="BBCA, BBRI"
            className="rounded-md border border-ink/20 bg-surface px-2.5 py-1.5 font-mono text-sm text-ink outline-none focus:border-ledger-green"
          />
        </label>
        <div className="flex flex-col gap-1 font-mono text-xs text-ink-muted">
          Indikator makro
          <div className="flex flex-wrap gap-2">
            {MACRO_OPTIONS.map((o) => (
              <label key={o.type} className="flex items-center gap-1 text-xs text-ink">
                <input
                  type="checkbox" checked={macroSelected.includes(o.type)}
                  onChange={() => setMacroSelected((prev) =>
                    prev.includes(o.type) ? prev.filter((t) => t !== o.type) : [...prev, o.type]
                  )}
                  className="accent-ledger-green"
                />
                {o.label}
              </label>
            ))}
          </div>
        </div>
        <div className="sm:col-span-3">
          <button
            type="submit"
            className="rounded-md border border-ledger-green bg-ledger-green px-4 py-2 font-mono text-sm text-parchment transition-colors hover:bg-ledger-green/90"
          >
            Bandingkan
          </button>
        </div>
      </form>

      {state.kind === "loading" ? (
        <div className="mt-8 h-64 animate-pulse rounded-lg bg-ink/5 sm:h-72" />
      ) : state.kind === "error" ? (
        <div className="mt-8">
          <ChartError message={state.message} onRetry={run} />
        </div>
      ) : state.kind === "ready" ? (
        <div className="mt-8">
          <div className="mb-4 flex flex-wrap gap-3">
            {state.series.map((s, i) => (
              <span key={s.id} className="inline-flex items-center gap-1.5 font-mono text-xs">
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colors[i % colors.length] }} />
                {s.label}
              </span>
            ))}
          </div>

          <div className="overflow-hidden rounded-lg border border-ink/10 bg-surface">
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
                  tickFormatter={(v: number) => fmtNumber(v, 1)}
                  tick={{ fill: CHART.axis, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                  axisLine={false} tickLine={false} width={48}
                  label={{ value: "Base 100", angle: -90, position: "insideLeft", offset: 4, fill: CHART.inkMuted, fontSize: 11, fontFamily: "var(--font-plex-mono)" }}
                />
                <Tooltip cursor={{ stroke: CHART.inkMuted, strokeDasharray: "3 3" }} offset={-26} content={<CompareTooltip series={state.series} />} />
                {state.series.map((s, i) => (
                  <Line
                    key={s.id}
                    dataKey={s.id}
                    type="monotone"
                    stroke={colors[i % colors.length]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                    connectNulls={false}
                    isAnimationActive={false}
                    name={s.label}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 rounded-md border border-ink/10 bg-parchment/50 p-3 font-mono text-xs text-ink-muted">
            <strong className="text-ink">Mengapa base 100?</strong> Yield obligasi (~0–12%), harga saham (ribuan Rupiah),
            dan indikator makro (beragam satuan) punya skala yang sangat berbeda. Dengan menetapkan nilai awal
            masing-masing seri sebagai 100, grafik di atas menunjukkan <em>perubahan relatif</em> misalnya nilai
            110 berarti naik 10% dari titik awal. Ini memungkinkan perbandingan yang adil antar kategori.
          </div>

          <ChartCaption source={sources} date={latestDate ? fmtDate(latestDate) : null}>
            <CsvButton onClick={handleCsv} />
          </ChartCaption>
        </div>
      ) : null}
    </section>
  );
}

function CompareTooltip({
  active, payload, series,
}: {
  active?: boolean;
  payload?: { dataKey: string | number; value: number; payload: Record<string, unknown> }[];
  series: SeriesItem[];
}) {
  if (!active || !payload?.length) return null;
  const t = payload[0]?.payload?.t as number | undefined;
  return (
    <ChartTooltip>
      <p className="font-medium text-ink">{t ? fmtDate(new Date(t).toISOString().slice(0, 10)) : ""}</p>
      {series.map((s) => {
        const p = payload.find((pp) => String(pp.dataKey) === s.id);
        return p ? (
          <TooltipRow key={s.id} label={s.label} value={`${fmtNumber(p.value, 1)} (base 100)`} />
        ) : null;
      })}
    </ChartTooltip>
  );
}

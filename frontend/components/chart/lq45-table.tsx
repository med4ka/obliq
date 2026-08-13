"use client";

import Link from "next/link";
import { ArrowUpDown, TrendingUp, TrendingDown, Minus, Search, BarChart3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiClientError, getStockList, toNumber } from "@/lib/api-client";
import type { StockListItem } from "@/lib/api-client";

import { fmtNumber } from "./chart-utils";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; items: StockListItem[] };

type SortKey = "code" | "name" | "sector" | "close" | "change";
type SortDir = "asc" | "desc";

export default function Lq45Table() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [query, setQuery] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("code");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    getStockList()
      .then((resp) => {
        if (resp.status === "empty" || resp.items.length === 0) {
          setState({ kind: "ready", items: [] });
          return;
        }
        setState({ kind: "ready", items: resp.items });
      })
      .catch((err: unknown) => {
        const msg =
          err instanceof ApiClientError
            ? err.message
            : "Gagal memuat daftar saham.";
        setState({ kind: "error", message: msg });
      });
  }, []);

  const sectors = useMemo(() => {
    if (state.kind !== "ready") return [];
    const set = new Set<string>();
    state.items.forEach((i) => { if (i.sector) set.add(i.sector); });
    return Array.from(set).sort();
  }, [state]);

  const filtered = useMemo(() => {
    if (state.kind !== "ready") return [];
    let list = state.items;
    if (query) {
      const q = query.toLowerCase();
      list = list.filter(
        (i) => i.code.toLowerCase().includes(q) || i.name.toLowerCase().includes(q)
      );
    }
    if (sectorFilter) {
      list = list.filter((i) => i.sector === sectorFilter);
    }
    list = [...list].sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "code": cmp = a.code.localeCompare(b.code); break;
        case "name": cmp = a.name.localeCompare(b.name); break;
        case "sector": cmp = (a.sector ?? "").localeCompare(b.sector ?? ""); break;
        case "close": cmp = (toNumber(a.latest_close) ?? 0) - (toNumber(b.latest_close) ?? 0); break;
        case "change": cmp = (toNumber(a.change_pct) ?? 0) - (toNumber(b.change_pct) ?? 0); break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return list;
  }, [state, query, sectorFilter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const toggleSelect = (code: string) => {
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return <ArrowUpDown className="ml-0.5 h-3 w-3 shrink-0 opacity-30" aria-hidden />;
    return <ArrowUpDown className={`ml-0.5 h-3 w-3 shrink-0 ${sortDir === "asc" ? "rotate-0" : "rotate-180"}`} aria-hidden />;
  };

  if (state.kind === "loading") {
    return (
      <div className="mt-6 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 animate-pulse rounded bg-ink/5" />
        ))}
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div role="alert" className="mt-6 rounded-md border border-seal-red/40 bg-seal-red/5 px-4 py-3">
        <p className="font-mono text-xs text-seal-red">{state.message}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-2 rounded border border-ink/20 px-2 py-1 font-mono text-[11px] text-ink transition-colors hover:bg-ink/5"
        >
          Coba lagi
        </button>
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden />
          <input
            type="text"
            placeholder="Cari kode atau nama..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full rounded-full border border-ink/10 bg-surface py-2 pl-8 pr-3 font-mono text-xs text-ink placeholder:text-ink-muted focus:border-ledger-green focus:outline-none sm:text-sm"
          />
        </div>

        <select
          value={sectorFilter}
          onChange={(e) => setSectorFilter(e.target.value)}
          className="rounded-full border border-ink/10 bg-surface px-3 py-2 font-mono text-xs text-ink focus:border-ledger-green focus:outline-none sm:text-sm"
        >
          <option value="">Semua sektor</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {selected.length >= 2 && (
          <Link
            href={`/saham/bandingkan?kode=${selected.join(",")}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-ledger-green/30 bg-ledger-green/5 px-3 py-2 font-mono text-xs text-ledger-green transition-colors hover:bg-ledger-green/10 sm:text-sm"
          >
            <BarChart3 className="h-4 w-4" aria-hidden />
            Bandingkan ({selected.length})
          </Link>
        )}
      </div>

      <p className="mt-2 font-mono text-xs text-ink-muted">
        {filtered.length} dari {state.kind === "ready" ? state.items.length : "?"} saham
        {selected.length > 0 && ` · ${selected.length} dipilih`}
      </p>

      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left font-mono text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-ink/10 text-ink-muted">
              <th className="w-8 py-2 pr-2" />
              <th className="cursor-pointer py-2 pr-3 font-medium" onClick={() => toggleSort("code")}>
                <span className="inline-flex items-center">Kode{sortIcon("code")}</span>
              </th>
              <th className="cursor-pointer py-2 pr-3 font-medium" onClick={() => toggleSort("name")}>
                <span className="inline-flex items-center">Nama{sortIcon("name")}</span>
              </th>
              <th className="hidden cursor-pointer py-2 pr-3 font-medium sm:table-cell" onClick={() => toggleSort("sector")}>
                <span className="inline-flex items-center">Sektor{sortIcon("sector")}</span>
              </th>
              <th className="cursor-pointer py-2 pr-3 text-right font-medium" onClick={() => toggleSort("close")}>
                <span className="inline-flex items-center justify-end">Terakhir{sortIcon("close")}</span>
              </th>
              <th className="cursor-pointer py-2 text-right font-medium" onClick={() => toggleSort("change")}>
                <span className="inline-flex items-center justify-end">Δ{sortIcon("change")}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr
                key={item.code}
                className="border-b border-ink/5 transition-colors hover:bg-ink/5"
              >
                <td className="py-2 pr-2">
                  <input
                    type="checkbox"
                    checked={selected.includes(item.code)}
                    onChange={() => toggleSelect(item.code)}
                    className="h-4 w-4 rounded border-ink/20 text-ledger-green focus:ring-ledger-green"
                    aria-label={`Pilih ${item.code}`}
                  />
                </td>
                <td className="py-2 pr-3">
                  <Link
                    href={`/saham/${item.code}`}
                    className="font-medium text-ledger-green underline-offset-2 hover:underline"
                  >
                    {item.code}
                  </Link>
                </td>
                <td className="py-2 pr-3 text-ink-muted">{item.name}</td>
                <td className="hidden py-2 pr-3 text-ink-muted sm:table-cell">
                  {item.sector ?? "—"}
                </td>
                <td className="py-2 pr-3 text-right tabular-nums text-ink">
                  {item.latest_close ? fmtNumber(toNumber(item.latest_close)) : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-ink">
                  {renderChange(item)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div className="mt-4 grid place-items-center rounded-md border border-dashed border-ink/10 bg-parchment px-4 py-8 font-mono text-xs text-ink-muted">
          Tidak ada saham yang cocok.
        </div>
      )}
    </div>
  );
}

function renderChange(item: StockListItem) {
  const change = toNumber(item.change);
  const pct = toNumber(item.change_pct);
  if (change === null || pct === null) {
    return <span className="text-ink-muted">—</span>;
  }

  let icon: React.ReactNode;
  let cls = "text-ink-muted";
  if (change > 0) {
    icon = <TrendingUp className="h-3 w-3 shrink-0" aria-hidden />;
    cls = "text-ink";
  } else if (change < 0) {
    icon = <TrendingDown className="h-3 w-3 shrink-0" aria-hidden />;
    cls = "text-ink";
  } else {
    icon = <Minus className="h-3 w-3 shrink-0" aria-hidden />;
  }

  return (
    <span className={`inline-flex items-center gap-1 ${cls}`}>
      {icon}
      <span>
        {change > 0 ? "+" : ""}
        {fmtNumber(change)}
      </span>
      <span className="text-ink-muted">
        ({change > 0 ? "+" : ""}
        {pct.toFixed(2)}%)
      </span>
    </span>
  );
}

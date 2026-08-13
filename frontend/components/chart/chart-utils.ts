/**
 * Shared chart helpers: DESIGN.md tokens as constants (Recharts needs raw hex,
 * not Tailwind classes, on SVG elements), display formatters, and the
 * time-series gap-break strategy.
 *
 * Gap handling (ARCHITECTURE.md §4): missing data is never silently joined.
 * `toTimePoints` inserts a `null` point at the midpoint of any date range
 * longer than `maxGapDays`, and charts are always rendered with
 * `connectNulls={false}` so the line visibly breaks instead of interpolating
 * across the hole.
 */
import { toNumber } from "@/lib/api-client";

export const CHART = {
  ledgerGreen: "#0F4C3A",
  ink: "#1F2419",
  inkMuted: "#6B6355",
  surface: "#FFFEF9",
  grid: "#E4DECE",
  axis: "#B4AC98",
  sealRed: "#8C2F1F",
  gold: "#A67C27",
} as const;

export const DUMMY_BADGE_TEXT = "DATA CONTOH — BELUM DARI SUMBER RESMI";

const MONTHS_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
  "Jul", "Agu", "Sep", "Okt", "Nov", "Des",
] as const;

export function parseDate(v: string | null | undefined): Date | null {
  if (!v) return null;
  const d = new Date(`${v.slice(0, 10)}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** "2026-08-04" -> "4 Agu 2026" (id-ID, manual to avoid TZ shifts). */
export function fmtDate(v: string | null | undefined): string {
  const d = parseDate(v);
  if (!d) return "—";
  return `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`;
}

/** Shorter date for axis labels: "2026-08-04" -> "Agu 26". ~40% shorter than fmtDate. */
export function fmtDateShort(v: string | null | undefined): string {
  const d = parseDate(v);
  if (!d) return "—";
  return `${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear() % 100}`;
}

/** 4.6344 -> "4,63%" — Indonesian decimal comma. */
export function fmtYield(
  v: number | null | undefined,
  ndigits = 2
): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${v.toFixed(ndigits)}`.replace(".", ",") + "%";
}

/** Tenor display: "23,4 th". */
export function fmtYears(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}`.replace(".", ",") + " th";
}

/** Number display with id-ID thousand separator. */
export function fmtNumber(
  v: number | null | undefined,
  ndigits = 0
): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toLocaleString("id-ID", { maximumFractionDigits: ndigits });
}

/** Time series point (x = epoch ms, y = value). */
export interface TimePoint {
  t: number;
  y: number | null;
}

/**
 * Build Recharts points, inserting a null at the midpoint of any date range
 * > maxGapDays so the line breaks there (connectNulls={false}). Null midpoints
 * never fabricate values — they only mark the absence of data.
 * Accepts raw API decimal strings ("4.6344") as well as numbers.
 */
export function toTimePoints(
  rows: { date: string | null; value: string | number | null | undefined }[],
  maxGapDays: number
): TimePoint[] {
  const out: TimePoint[] = [];
  for (let i = 0; i < rows.length; i++) {
    const prev = parseDate(rows[i - 1]?.date);
    const cur = parseDate(rows[i].date);
    if (i > 0 && prev && cur) {
      const gap = (cur.getTime() - prev.getTime()) / 86_400_000;
      if (gap > maxGapDays) {
        out.push({ t: (prev.getTime() + cur.getTime()) / 2, y: null });
      }
    }
    out.push({
      t: cur?.getTime() ?? 0,
      y: toNumber(rows[i].value as string | null | undefined),
    });
  }
  return out;
}
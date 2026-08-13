"use client";

const RANGES = [
  { key: "1M", label: "1B", days: 30 },
  { key: "6M", label: "6B", days: 180 },
  { key: "1Y", label: "1T", days: 365 },
  { key: "3Y", label: "3T", days: 1095 },
  { key: "ALL", label: "Semua", days: Infinity },
] as const;

export type RangeKey = (typeof RANGES)[number]["key"];

export function filterByRange<T extends { t: number }>(
  points: T[],
  range: RangeKey
): T[] {
  if (range === "ALL" || points.length === 0) return points;
  const r = RANGES.find((r) => r.key === range)!;
  const cutoff = Date.now() - r.days * 86_400_000;
  return points.filter((p) => p.t >= cutoff);
}

export function TimeframeSelector({
  value,
  onChange,
}: {
  value: RangeKey;
  onChange: (k: RangeKey) => void;
}) {
  return (
    <div className="flex gap-1 font-mono text-xs">
      {RANGES.map((r) => (
        <button
          key={r.key}
          type="button"
          onClick={() => onChange(r.key)}
          className={`rounded-full px-2.5 py-1 transition-colors ${
            value === r.key
              ? "bg-ledger-green text-parchment"
              : "bg-ink/5 text-ink-muted hover:bg-ink/10 hover:text-ink"
          }`}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

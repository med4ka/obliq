/**
 * Chart skeleton — wavy grey placeholder in the shape of a chart
 * (DESIGN.md §4: "bentuk chart placeholder — garis abu-abu bergelombang,
 * bukan blok generik"), rendered while real chart data loads.
 *
 * The wave is pure SVG (no script), so it works server-side rendered too.
 */
export default function ChartSkeleton() {
  return (
    <div className="animate-pulse">
      <svg
        viewBox="0 0 600 200"
        preserveAspectRatio="none"
        aria-hidden="true"
        className="h-48 w-full sm:h-64 md:h-72"
      >
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
  );
}
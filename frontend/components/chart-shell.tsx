/**
 * Responsive container for charts.
 *
 * Charts (Recharts, DESIGN.md §7.3) are rendered inside this shell with
 * width:100% so they scale from mobile (375px) to desktop instead of fixing
 * a pixel width. Height is set via responsive Tailwind utilities supplied by
 * the caller (default ~16:9-ish band, collapsing on small screens).
 *
 * Charts are lazy-loaded with next/dynamic + ssr:false (they need browser
 * APIs for SVG measure/hover). Until the chunk loads, ChartSkeleton renders.
 */
export default function ChartShell({
  children,
  ariaLabel,
}: {
  children: React.ReactNode;
  ariaLabel?: string;
}) {
  return (
    <div
      role="img"
      aria-label={ariaLabel ?? "Chart"}
      className="w-full overflow-hidden rounded-lg border border-ink/10 bg-surface"
    >
      {children}
    </div>
  );
}
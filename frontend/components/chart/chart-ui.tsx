/**
 * Presentational building blocks shared by chart components: the custom
 * tooltip surface, the mandatory source+date caption (SYSTEM.md §1 poin 2-3,
 * DESIGN.md §4), the DUMMY badge (RULES.md §3) and honest error/empty panels.
 * All pure presentational — no data logic here.
 */

/** Rendered by Recharts `<Tooltip content={...} />`. */
export function ChartTooltip({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="pointer-events-none rounded-md border border-ink/15 bg-surface px-3 py-2 font-mono text-xs text-ink shadow-sm">
      {children}
    </div>
  );
}

export function TooltipRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="text-ink-muted">{label}</span>
      <span className="text-right">{value}</span>
    </div>
  );
}

/** Source + freshness line under every chart. */
export function ChartCaption({
  source,
  date,
  children,
}: {
  source: string;
  date?: string | null;
  children?: React.ReactNode;
}) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-ink-muted">
      <span>{"Sumber: "}{source}</span>
      {date ? <span>{"Data per "}{date}</span> : null}
      {children}
    </div>
  );
}

/** RULES.md §3 — dummy data is never silent. */
export function DummyBadge() {
  return (
    <span className="inline-flex items-center rounded border border-seal-red/50 bg-seal-red/5 px-1.5 py-0.5 font-serif text-[11px] font-semibold text-seal-red">
      DATA CONTOH — BELUM DARI SUMBER RESMI
    </span>
  );
}

/** Honest empty state (SYSTEM.md §1 poin 1): never fabricate a curve. */
export function ChartEmpty({ message = "Data tidak tersedia." }: { message?: string }) {
  return (
    <div className="grid h-64 place-items-center rounded-md border border-dashed border-ink/10 bg-parchment px-4 text-center font-mono text-xs text-ink-muted sm:h-72">
      {message}
    </div>
  );
}

/** API down / malformed response, with retry action. */
export function ChartError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="rounded-md border border-seal-red/40 bg-seal-red/5 px-4 py-3"
    >
      <p className="font-mono text-xs text-seal-red">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded border border-ink/20 px-2 py-1 font-mono text-[11px] text-ink transition-colors hover:bg-ink/5"
        >
          Coba lagi
        </button>
      ) : null}
    </div>
  );
}

/** CSV download button — rendered inside chart caption. */
export function CsvButton({
  onClick,
}: {
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="ml-auto rounded border border-ink/15 px-2 py-0.5 font-mono text-[11px] text-ink-muted transition-colors hover:border-ink/30 hover:text-ink"
    >
      Unduh CSV
    </button>
  );
}
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

export default function ChartModal({
  children,
  label,
}: {
  children: React.ReactNode;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group relative w-full cursor-zoom-in text-left"
        aria-label={label ? `Perbesar grafik: ${label}` : "Perbesar grafik"}
      >
        {children}
      </button>

      {open &&
        createPortal(
          <div
            ref={backdropRef}
            role="dialog"
            aria-modal="true"
            aria-label={label ?? "Grafik diperbesar"}
            onClick={(e) => {
              if (e.target === backdropRef.current) close();
            }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-2 sm:p-6"
          >
            <div className="relative flex w-full max-w-5xl flex-col rounded-2xl border border-ink/10 bg-surface shadow-xl">
              <div className="flex items-center justify-between border-b border-ink/10 px-4 py-3 sm:px-6">
                <span className="font-serif text-sm font-semibold text-ink sm:text-base">
                  {label ?? "Grafik"}
                </span>
                <button
                  ref={closeRef}
                  type="button"
                  onClick={close}
                  aria-label="Tutup"
                  className="grid h-9 w-9 place-items-center rounded-full text-ink-muted transition-colors hover:bg-ink/5 hover:text-ink"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="overflow-hidden p-2 sm:p-4">
                <div className="[&_*]:!cursor-default">
                  {children}
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
}

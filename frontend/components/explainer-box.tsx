"use client";

import { ChevronDown } from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";

interface Props {
  title: string;
  titleId: string;
  children: ReactNode;
}

export default function ExplainerBox({ title, titleId, children }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section
      className="mt-8 rounded-lg border border-ink/10 bg-surface"
      aria-labelledby={titleId}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={`${titleId}-content`}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left transition-colors hover:bg-ink/[0.02] sm:px-6"
      >
        <h2
          id={titleId}
          className="font-serif text-lg font-semibold text-ink sm:text-xl"
        >
          {title}
        </h2>
        <ChevronDown
          aria-hidden
          className={`h-5 w-5 shrink-0 text-ink-muted transition-transform duration-300 motion-reduce:transition-none ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      <div
        id={`${titleId}-content`}
        className={`overflow-hidden transition-[max-height] duration-300 motion-reduce:transition-none ${
          open ? "max-h-[1000px]" : "max-h-0"
        }`}
      >
        <div className="px-5 pb-5 sm:px-6 sm:pb-6">{children}</div>
      </div>
    </section>
  );
}

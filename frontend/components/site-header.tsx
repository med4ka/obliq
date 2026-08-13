"use client";

import { BookOpen, GitCompare, LineChart, Menu, ScrollText, TrendingUp, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Kurva Yield", icon: LineChart },
  { href: "/saham", label: "IHSG", icon: TrendingUp },
  { href: "/makro", label: "Indikator Makro", icon: ScrollText },
  { href: "/bandingkan", label: "Bandingkan", icon: GitCompare },
];

const LEARN_ITEM = { href: "/belajar", label: "Belajar", icon: BookOpen };

export default function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) => pathname === href;

  return (
    <header className="sticky top-0 z-50 w-full">
      <div className="px-4 pt-3 sm:pt-4">
        <div
          className={`mx-auto max-w-5xl border border-ink/10 bg-surface shadow-sm ${
            open ? "rounded-3xl" : "rounded-full"
          }`}
        >
          <div className="flex items-center justify-between gap-3 px-3 py-2 sm:gap-4 sm:px-5">
            <Link
              href="/"
              className="group flex shrink-0 items-center gap-2.5"
              onClick={() => setOpen(false)}
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-ledger-green/40 bg-parchment font-serif text-base font-semibold text-ledger-green sm:h-8 sm:w-8 sm:text-lg">
                O
              </span>
              <span className="whitespace-nowrap font-serif text-lg font-semibold tracking-wide text-ink">
                Obliq
              </span>
            </Link>

            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-controls="site-nav"
              aria-label={open ? "Tutup menu" : "Buka menu"}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-ink-muted transition-colors hover:bg-ink/5 hover:text-ink md:hidden"
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>

            <nav
              id="site-nav"
              aria-label="Navigasi utama"
              className="hidden items-center gap-1 md:flex"
            >
              {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                      active
                        ? "bg-ledger-green text-parchment"
                        : "text-ink-muted hover:bg-ink/5 hover:text-ink"
                    }`}
                  >
                    <Icon className="h-4 w-4" aria-hidden />
                    <span>{label}</span>
                  </Link>
                );
              })}
            </nav>

            <Link
              href={LEARN_ITEM.href}
              className={`hidden items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-colors md:flex ${
                isActive(LEARN_ITEM.href)
                  ? "border-ledger-green bg-ledger-green text-parchment"
                  : "border-ledger-green/30 bg-ledger-green/5 text-ledger-green hover:border-ledger-green/60 hover:bg-ledger-green/10"
              }`}
            >
              <LEARN_ITEM.icon className="h-4 w-4" aria-hidden />
              <span>{LEARN_ITEM.label}</span>
            </Link>
          </div>

          {open && (
            <nav
              aria-label="Navigasi mobile"
              className="flex flex-col gap-1.5 border-t border-ink/10 px-3 py-3 sm:px-5 md:hidden"
            >
              {[...NAV_ITEMS, LEARN_ITEM].map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={`flex min-h-11 w-full items-center gap-3 rounded-full px-3.5 text-sm transition-colors ${
                      active
                        ? "bg-ledger-green text-parchment"
                        : "text-ink-muted hover:bg-ink/5 hover:text-ink"
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden />
                    <span className="whitespace-nowrap">{label}</span>
                  </Link>
                );
              })}
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}

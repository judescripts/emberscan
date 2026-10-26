"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { IconBuildings, IconReport, IconScan, IconTasks } from "./icons";
import { cx } from "./ui";

export const TABS = [
  { href: "/", label: "Buildings", Icon: IconBuildings, match: (p: string) => p === "/" },
  { href: "/scan", label: "New scan", Icon: IconScan, match: (p: string) => p.startsWith("/scan") },
  { href: "/report", label: "Report", Icon: IconReport, match: (p: string) => p.startsWith("/report") },
  { href: "/hoa", label: "HOA tasks", Icon: IconTasks, match: (p: string) => p.startsWith("/hoa") },
];

/** Phones: solid tab bar docked to the bottom edge, icons above labels. */
export function BottomTabs() {
  const path = usePathname() ?? "/";
  return (
    <nav
      aria-label="Main"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-black/20 bg-nav pb-[env(safe-area-inset-bottom)] lg:hidden"
    >
      <ul className="grid grid-cols-4">
        {TABS.map(({ href, label, Icon, match }) => {
          const active = match(path);
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className="flex flex-col items-center gap-0.5 px-1 py-2 text-[11px] font-semibold"
              >
                <span
                  className={cx(
                    "flex h-7 w-14 items-center justify-center rounded-full",
                    active ? "bg-nav-pill text-nav-pill-fg" : "text-nav-label",
                  )}
                >
                  <Icon size={20} />
                </span>
                <span className={active ? "text-white" : "text-nav-label"}>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** Tablets and up: the same tabs as pills in the top bar. */
export function TopTabs() {
  const path = usePathname() ?? "/";
  return (
    <nav aria-label="Main" className="hidden lg:block">
      <ul className="flex items-center gap-1">
        {[...TABS, { href: "/rules", label: "Rules", Icon: null, match: (p: string) => p.startsWith("/rules") }].map(
          ({ href, label, match }) => {
            const active = match(path);
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cx(
                    "rounded-full px-3 py-1.5 text-sm font-semibold whitespace-nowrap",
                    active ? "bg-nav-pill text-nav-pill-fg" : "text-nav-label hover:text-white",
                  )}
                >
                  {label}
                </Link>
              </li>
            );
          },
        )}
      </ul>
    </nav>
  );
}

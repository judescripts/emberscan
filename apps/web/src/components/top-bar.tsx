import Link from "next/link";
import { currentContext } from "@/lib/current";
import { CommunitySwitcher } from "./community-switcher";
import { Flame } from "./icons";
import { TopTabs } from "./nav";
import { ThemeToggle } from "./theme-toggle";

function Logo() {
  return (
    <Link href="/" className="flex shrink-0 items-center gap-1.5 text-white" aria-label="EmberScan home">
      <Flame />
      <span className="text-[15px] font-bold tracking-tight sm:text-base">EmberScan</span>
    </Link>
  );
}

function Bar({ children }: { children?: React.ReactNode }) {
  return (
    <header className="sticky top-0 z-40 bg-nav">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-3 sm:gap-3 sm:px-4">
        <Logo />
        {children}
      </div>
    </header>
  );
}

export function TopBarShell() {
  return (
    <Bar>
      <div className="flex-1" />
    </Bar>
  );
}

export async function TopBar() {
  const { communities, current } = await currentContext();
  return (
    <Bar>
      <CommunitySwitcher
        communities={communities.map((c) => ({ id: c.id, name: c.name, isSample: c.isSample }))}
        currentId={current?.id ?? null}
      />
      <div className="hidden flex-1 justify-center md:flex">
        <TopTabs />
      </div>
      <Link
        href="/manage"
        className="hidden rounded-full border border-white/20 px-3 py-1.5 text-sm font-semibold text-nav-label hover:text-white sm:inline-block"
      >
        Manage
      </Link>
      <ThemeToggle />
    </Bar>
  );
}

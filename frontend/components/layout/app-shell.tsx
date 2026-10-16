"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Building2,
  ChevronDown,
  Crosshair,
  GitBranch,
  LayoutDashboard,
  ListChecks,
  Radar,
  Search,
  ShieldCheck
} from "lucide-react";
import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import { DemoUserSwitch } from "@/components/demo-user-switch";
import type { DemoSession } from "@/lib/api";

const primaryItem = { href: "/browser-tasks", label: "AI 搜索候选人", icon: Search };

const navGroups = [
  {
    key: "talent",
    label: "人才工作台",
    icon: Crosshair,
    items: [
      { href: "/talent-pool", label: "人才猎场", icon: Crosshair },
      { href: "/candidates", label: "人才库", icon: ListChecks }
    ]
  },
  {
    key: "intel",
    label: "情报总览",
    icon: LayoutDashboard,
    items: [
      { href: "/dashboard", label: "总览", icon: LayoutDashboard },
      { href: "/analytics", label: "效能分析", icon: BarChart3 },
      { href: "/org-graph", label: "组织架构", icon: GitBranch },
      { href: "/manager", label: "管理者视图", icon: ShieldCheck },
      { href: "/companies", label: "公司监测", icon: Building2 },
      { href: "/settings", label: "工作区设置", icon: ShieldCheck }
    ]
  }
];

function itemActive(pathname: string, href: string) {
  if (href === "/candidates") return pathname === "/candidates" || pathname.startsWith("/candidates/");
  return pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
}

function groupActive(pathname: string, group: (typeof navGroups)[number]) {
  return group.items.some((item) => itemActive(pathname, item.href));
}

export function AppShell({ children, session }: { children: React.ReactNode; session: DemoSession | null }) {
  const pathname = usePathname();
  const initialOpen = useMemo(() => {
    const active = navGroups.find((group) => groupActive(pathname, group));
    return active?.key ?? "talent";
  }, [pathname]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({
    [initialOpen]: true
  });

  function toggleGroup(key: string) {
    setOpenGroups((current) => ({ ...current, [key]: !current[key] }));
  }

  const PrimaryIcon = primaryItem.icon;
  const primaryActive = itemActive(pathname, primaryItem.href);

  return (
    <div className="min-h-[100dvh]">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-sm focus:text-primary-foreground"
      >
        跳到主内容
      </a>

      <aside className="fixed inset-y-0 left-0 z-20 hidden w-72 bg-[#071014] text-white shadow-[24px_0_80px_hsl(207_70%_8%_/_0.22)] lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b border-white/10 px-5 py-5">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-lg bg-accent text-slate-950 shadow-[inset_0_1px_1px_hsl(0_0%_100%_/_0.35)]">
                <Radar className="h-5 w-5" />
              </div>
              <div>
                <p className="text-lg font-black leading-none">TalentNet</p>
                <p className="mt-1 text-xs text-slate-400">AI recruiting workflow</p>
              </div>
            </div>
          </div>

          <nav className="flex-1 space-y-2 px-3 py-4" aria-label="主导航">
            <Link
              href={primaryItem.href}
              aria-current={primaryActive ? "page" : undefined}
              className={cn(
                "flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold text-slate-300 transition hover:bg-white/[0.07] hover:text-white",
                primaryActive &&
                  "bg-white text-slate-950 shadow-[0_12px_28px_hsl(0_0%_0%_/_0.24)] hover:bg-white hover:text-slate-950"
              )}
            >
              <PrimaryIcon className="h-4 w-4 shrink-0" strokeWidth={2.1} />
              {primaryItem.label}
            </Link>

            {navGroups.map((group) => {
              const Icon = group.icon;
              const active = groupActive(pathname, group);
              const open = openGroups[group.key] || active;
              return (
                <div key={group.key}>
                  <button
                    type="button"
                    onClick={() => toggleGroup(group.key)}
                    className={cn(
                      "flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-sm font-semibold text-slate-300 transition hover:bg-white/[0.07] hover:text-white",
                      active &&
                        "bg-white text-slate-950 shadow-[0_12px_28px_hsl(0_0%_0%_/_0.24)] hover:bg-white hover:text-slate-950"
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" strokeWidth={2.1} />
                    <span className="flex-1">{group.label}</span>
                    <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
                  </button>
                  {open ? (
                    <div className="mt-1 grid gap-1 border-l border-white/10 pl-4">
                      {group.items.filter(item => item.href !== "/manager" || session?.role === "admin").map((item) => {
                        const ItemIcon = item.icon;
                        const childActive = itemActive(pathname, item.href);
                        return (
                          <Link
                            key={item.href}
                            href={item.href}
                            aria-current={childActive ? "page" : undefined}
                            className={cn(
                              "flex min-h-9 items-center gap-2 rounded-md px-3 text-xs font-bold text-slate-400 transition hover:bg-white/[0.07] hover:text-white",
                              childActive && "bg-white/[0.1] text-white"
                            )}
                          >
                            <ItemIcon className="h-3.5 w-3.5" strokeWidth={2.1} />
                            {item.label}
                          </Link>
                        );
                      })}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </nav>

          <div className="border-t border-white/10 px-5 py-4 text-xs leading-5 text-slate-400">
            AI 搜索保持一级入口，其余资产和分析折叠到对应模块。
          </div>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-border bg-background/88 backdrop-blur-xl">
          <div className="mx-auto flex w-full max-w-[1360px] items-center justify-between gap-4 px-4 py-3 sm:px-6">
            <div>
              <p className="text-sm font-black">TalentNet</p>
              <p className="mt-0.5 text-xs text-muted-foreground">搜索、入库、猎场跟进、情报复盘</p>
            </div>
            <DemoUserSwitch session={session} />
          </div>
          <nav className="flex gap-2 overflow-x-auto border-t border-border px-4 py-2 lg:hidden" aria-label="移动端导航">
            {[primaryItem, ...navGroups.flatMap((group) => group.items)].filter(item => item.href !== "/manager" || session?.role === "admin").map((item) => {
              const Icon = item.icon;
              const active = itemActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "inline-flex shrink-0 items-center gap-2 rounded-md border bg-white px-3 py-2 text-sm font-bold text-slate-700 active:scale-[0.99]",
                    active && "border-primary bg-primary text-primary-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" strokeWidth={2.1} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>

        <main id="main-content" className="mx-auto w-full max-w-[1360px] px-4 py-5 sm:px-6">
          {children}
        </main>
      </div>
    </div>
  );
}

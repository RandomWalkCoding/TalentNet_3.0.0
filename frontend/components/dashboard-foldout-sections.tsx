"use client";

import Link from "next/link";
import { ChevronDown, GitBranch } from "lucide-react";
import { useState } from "react";

import type { Company } from "@/lib/api";

export function DashboardFoldoutSections({ companies }: { companies: Company[] }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="tn-surface rounded-lg">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
      >
        <div>
          <h2 className="font-black">公司与组织信息</h2>
          <p className="mt-1 text-xs text-muted-foreground">默认收起，需要时再查看公司覆盖和组织架构。</p>
        </div>
        <ChevronDown className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`} />
      </button>
      {open ? (
        <div className="grid gap-3 border-t border-border p-5 md:grid-cols-3">
          {companies.map((company) => (
            <div key={company.id} className="rounded-md border bg-white p-4">
              <p className="font-black">{company.name}</p>
              <p className="mt-1 text-sm text-muted-foreground">{company.industry}</p>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <p>
                  候选人：<span className="font-black">{company.candidate_count}</span>
                </p>
                <p>
                  高风险：<span className="font-black text-red-700">{company.high_risk_count}</span>
                </p>
              </div>
            </div>
          ))}
          <Link href="/org-graph" className="rounded-md border bg-white p-4 transition hover:border-primary/40 hover:bg-muted/40">
            <GitBranch className="h-4 w-4 text-primary" />
            <p className="mt-3 font-black">打开组织架构</p>
            <p className="mt-1 text-sm text-muted-foreground">按公司、部门、候选人查看层级关系。</p>
          </Link>
        </div>
      ) : null}
    </section>
  );
}

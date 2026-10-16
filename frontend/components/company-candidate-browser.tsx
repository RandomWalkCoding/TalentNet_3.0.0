"use client";

import Link from "next/link";
import { ChevronDown, FileUp, Users } from "lucide-react";
import { useMemo, useState } from "react";

import { CompanyWebSearchButton } from "@/components/company-web-search-button";
import { RiskBadge } from "@/components/risk-badge";
import { CompanyEditForm } from "@/components/profile-edit-forms";
import type { CandidateListItem, Company } from "@/lib/api";

export function CompanyCandidateBrowser({
  companies,
  candidates
}: {
  companies: Company[];
  candidates: CandidateListItem[];
}) {
  const [openCompanyId, setOpenCompanyId] = useState(companies[0]?.id ?? "");
  const candidatesByCompany = useMemo(() => {
    return candidates.reduce<Record<string, CandidateListItem[]>>((acc, candidate) => {
      acc[candidate.current_company_id] = acc[candidate.current_company_id] ?? [];
      acc[candidate.current_company_id].push(candidate);
      return acc;
    }, {});
  }, [candidates]);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {companies.map((company) => {
        const related = candidatesByCompany[company.id] ?? [];
        const isOpen = openCompanyId === company.id;
        return (
          <article key={company.id} className="tn-surface rounded-lg">
            <button
              type="button"
              onClick={() => setOpenCompanyId(isOpen ? "" : company.id)}
              className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left"
            >
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <span className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground">
                    <Users className="h-4 w-4" />
                  </span>
                  <span className="rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
                    {company.monitor_status}
                  </span>
                </div>
                <h2 className="text-lg font-black">{company.name}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{company.industry}</p>
              </div>
              <ChevronDown className={`mt-2 h-4 w-4 transition ${isOpen ? "rotate-180" : ""}`} />
            </button>

            <div className="grid grid-cols-2 divide-x divide-border border-y border-border">
              <div className="p-5">
                <p className="text-sm font-bold text-muted-foreground">监测候选人</p>
                <p className="mt-2 text-3xl font-black">{related.length || company.candidate_count}</p>
              </div>
              <div className="p-5">
                <p className="text-sm font-bold text-muted-foreground">高风险</p>
                <p className="mt-2 text-3xl font-black text-red-700">{company.high_risk_count}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
              <button
                type="button"
                onClick={() => setOpenCompanyId(isOpen ? "" : company.id)}
                className="tn-button tn-button-secondary"
              >
                <Users className="h-4 w-4" />
                查看相关候选人
              </button>
              <div className="flex flex-wrap items-start gap-3">
                <CompanyWebSearchButton companyId={company.id} companyName={company.name} industry={company.industry} />
                <Link href="/candidates#candidate-upload" className="tn-button tn-button-primary">
                  <FileUp className="h-4 w-4" />
                  上传候选人
                </Link>
              </div>
            </div>

            {isOpen ? (
              <div className="border-t border-border px-5 py-4">
                {related.length ? (
                  <div className="grid gap-3">
                    {related.map((candidate) => (
                      <Link
                        key={candidate.id}
                        href={`/candidates/${candidate.id}`}
                        className="rounded-md border bg-white p-3 transition hover:border-primary/40 hover:bg-muted/40"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="font-black">{candidate.name}</p>
                          <RiskBadge level={candidate.risk_level} />
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {candidate.title} / {candidate.department ?? "未标注部门"}
                        </p>
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-md border bg-white p-4 text-sm leading-6 text-muted-foreground">
                    这家公司还没有候选人。可以上传文件，或直接联网搜索公开页面并确认入库。
                  </div>
                )}
              </div>
            ) : null}
            <CompanyEditForm company={company} />
          </article>
        );
      })}
    </div>
  );
}

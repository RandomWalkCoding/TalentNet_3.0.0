"use client";

import Link from "next/link";
import { Building2, ChevronDown, FileText, UsersRound } from "lucide-react";
import { useMemo, useState } from "react";

import { CompanyWebSearchButton } from "@/components/company-web-search-button";
import { RiskBadge } from "@/components/risk-badge";
import type { Company, OrgGraphNode, OrgGraphResponse } from "@/lib/api";

type CandidateRow = {
  id: string;
  name: string;
  title: string;
  department: string;
  domain: string;
  status: string;
  riskLevel: string | null;
  riskScore: number | null;
  evidenceCount: number;
};

type CompanySummary = {
  id: string;
  name: string;
  industry: string;
  status: string;
  departments: Record<string, CandidateRow[]>;
  candidateCount: number;
  evidenceCount: number;
  highRiskCount: number;
};

export function OrgGraphView({ graph, companies }: { graph: OrgGraphResponse; companies: Company[] }) {
  const [companyId, setCompanyId] = useState("");
  const [department, setDepartment] = useState("");
  const [domain, setDomain] = useState("");
  const [status, setStatus] = useState("");
  const [openCompanyId, setOpenCompanyId] = useState("");

  const summaries = useMemo(() => buildSummaries(graph, companies), [graph, companies]);
  const departments = useMemo(
    () => unique(summaries.flatMap((company) => Object.keys(company.departments))),
    [summaries]
  );
  const domains = useMemo(
    () =>
      unique(
        summaries.flatMap((company) =>
          Object.values(company.departments).flatMap((rows) => rows.map((row) => row.domain).filter(Boolean))
        )
      ),
    [summaries]
  );
  const statuses = useMemo(
    () =>
      unique(
        summaries.flatMap((company) =>
          Object.values(company.departments).flatMap((rows) => rows.map((row) => row.status).filter(Boolean))
        )
      ),
    [summaries]
  );

  const filtered = summaries
    .filter((company) => !companyId || company.id === companyId)
    .map((company) => {
      const nextDepartments: Record<string, CandidateRow[]> = Object.fromEntries(
        Object.entries(company.departments)
          .map(([departmentName, rows]) => [
            departmentName,
            rows.filter((row) => {
              const matchesDepartment = !department || departmentName === department;
              const matchesDomain = !domain || row.domain === domain;
              const matchesStatus = !status || row.status === status;
              return matchesDepartment && matchesDomain && matchesStatus;
            })
          ])
          .filter(([, rows]) => rows.length > 0)
      );
      const candidateCount = Object.values(nextDepartments).reduce((total, rows) => total + rows.length, 0);
      const evidenceCount = Object.values(nextDepartments).reduce(
        (total, rows) => total + rows.reduce((sum, row) => sum + row.evidenceCount, 0),
        0
      );
      const highRiskCount = Object.values(nextDepartments).reduce(
        (total, rows) => total + rows.filter((row) => ["very_high", "high"].includes(row.riskLevel ?? "")).length,
        0
      );
      return { ...company, departments: nextDepartments, candidateCount, evidenceCount, highRiskCount };
    })
    .filter((company) => company.candidateCount > 0 || (!department && !domain && !status));

  return (
    <section className="tn-surface rounded-lg">
      <div className="border-b border-border p-5">
        <h2 className="text-lg font-black">组织层级概览</h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
          用公司、部门、候选人三层结构替代图谱画布。公司是一级分组；同名部门只显示在所属公司下，便于快速扫描和进入候选人详情。
        </p>
      </div>

      <div className="grid gap-3 border-b border-border p-5 md:grid-cols-4">
        <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} className="tn-field">
          <option value="">全部公司</option>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
        <select value={department} onChange={(event) => setDepartment(event.target.value)} className="tn-field">
          <option value="">全部部门</option>
          {departments.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select value={domain} onChange={(event) => setDomain(event.target.value)} className="tn-field">
          <option value="">全部方向</option>
          {domains.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select value={status} onChange={(event) => setStatus(event.target.value)} className="tn-field">
          <option value="">全部状态</option>
          {statuses.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </div>

      <div className="divide-y divide-border">
        {filtered.map((company) => {
          const isOpen = openCompanyId === company.id || filtered.length === 1;
          return (
            <article key={company.id}>
              <button
                type="button"
                onClick={() => setOpenCompanyId(isOpen ? "" : company.id)}
                className="grid w-full gap-4 px-5 py-4 text-left lg:grid-cols-[1fr_auto]"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground">
                    <Building2 className="h-4 w-4" />
                  </span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-black">{company.name}</h3>
                      <span className="rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
                        {company.status}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">{company.industry}</p>
                  </div>
                </div>
                <div className="grid grid-cols-4 items-center gap-3 text-sm lg:min-w-[28rem]">
                  <Metric label="部门" value={Object.keys(company.departments).length} />
                  <Metric label="候选人" value={company.candidateCount} />
                  <Metric label="高风险" value={company.highRiskCount} danger />
                  <Metric label="证据" value={company.evidenceCount} />
                  <ChevronDown className={`ml-auto h-4 w-4 transition ${isOpen ? "rotate-180" : ""}`} />
                </div>
              </button>

              {isOpen ? (
                <div className="bg-muted/35 px-5 pb-5">
                  <div className="flex justify-end pt-3">
                    <CompanyWebSearchButton companyId={company.id} companyName={company.name} industry={company.industry} />
                  </div>
                  <div className="grid gap-3 pt-3">
                    {Object.entries(company.departments).map(([departmentName, rows]) => (
                      <div key={`${company.id}-${departmentName}`} className="rounded-lg border bg-white">
                        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
                          <div>
                            <p className="font-black">{departmentName}</p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {rows.length} 位候选人，{rows.reduce((total, row) => total + row.evidenceCount, 0)} 条证据
                            </p>
                          </div>
                          <UsersRound className="h-4 w-4 text-primary" />
                        </div>
                        <div className="divide-y divide-border">
                          {rows.map((row) => (
                            <Link
                              key={row.id}
                              href={`/candidates/${row.id}`}
                              className="grid gap-3 px-4 py-3 transition hover:bg-muted/45 md:grid-cols-[1fr_auto]"
                            >
                              <div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <p className="font-black">{row.name}</p>
                                  <RiskBadge level={row.riskLevel} />
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  {row.title} / {row.domain || "未标注方向"}
                                </p>
                              </div>
                              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                                <span>{row.status}</span>
                                <span className="inline-flex items-center gap-1">
                                  <FileText className="h-4 w-4" />
                                  {row.evidenceCount}
                                </span>
                              </div>
                            </Link>
                          ))}
                        </div>
                      </div>
                    ))}
                    {Object.keys(company.departments).length === 0 ? (
                      <div className="rounded-md border bg-white p-4 text-sm text-muted-foreground">
                        当前筛选下没有匹配的候选人。
                      </div>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function Metric({ label, value, danger = false }: { label: string; value: number; danger?: boolean }) {
  return (
    <div>
      <p className="text-xs font-bold text-muted-foreground">{label}</p>
      <p className={`mt-1 text-lg font-black ${danger ? "text-red-700" : ""}`}>{value}</p>
    </div>
  );
}

function buildSummaries(graph: OrgGraphResponse, companies: Company[]) {
  const evidenceCountByCandidate = graph.edges.reduce<Record<string, number>>((acc, edge) => {
    if (edge.relation === "supported_by" && edge.source.startsWith("candidate:")) {
      acc[edge.source] = (acc[edge.source] ?? 0) + 1;
    }
    return acc;
  }, {});

  const companyById = companies.reduce<Record<string, Company>>((acc, company) => {
    acc[company.id] = company;
    return acc;
  }, {});

  const summaries = new Map<string, CompanySummary>();
  for (const node of graph.nodes) {
    if (node.type !== "candidate") continue;
    const companyId = String(node.meta?.company_id ?? "");
    if (!companyId) continue;
    const company = companyById[companyId];
    if (!company) continue;
    const summary =
      summaries.get(companyId) ??
      {
        id: company.id,
        name: company.name,
        industry: company.industry,
        status: company.monitor_status,
        departments: {},
        candidateCount: 0,
        evidenceCount: 0,
        highRiskCount: 0
      };
    const department = String(node.meta?.department ?? "未标注部门");
    const row = candidateRow(node, evidenceCountByCandidate[node.id] ?? 0);
    summary.departments[department] = summary.departments[department] ?? [];
    summary.departments[department].push(row);
    summary.candidateCount += 1;
    summary.evidenceCount += row.evidenceCount;
    if (["very_high", "high"].includes(row.riskLevel ?? "")) summary.highRiskCount += 1;
    summaries.set(companyId, summary);
  }

  return [...summaries.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function candidateRow(node: OrgGraphNode, evidenceCount: number): CandidateRow {
  const candidateId = node.id.replace(/^candidate:/, "");
  return {
    id: candidateId,
    name: node.label,
    title: String(node.meta?.title ?? "未标注岗位"),
    department: String(node.meta?.department ?? "未标注部门"),
    domain: String(node.meta?.domain ?? ""),
    status: node.status,
    riskLevel: node.meta?.risk_level ? String(node.meta.risk_level) : null,
    riskScore: typeof node.meta?.risk_score === "number" ? node.meta.risk_score : null,
    evidenceCount
  };
}

function unique(values: string[]) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

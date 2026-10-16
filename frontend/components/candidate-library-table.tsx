"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { RiskBadge } from "@/components/risk-badge";
import type { CandidateListItem, Company } from "@/lib/api";
import { RISK_LEVEL_LABELS } from "@/lib/labels";

export function CandidateLibraryTable({
  candidates,
  companies
}: {
  candidates: CandidateListItem[];
  companies: Company[];
}) {
  const [query, setQuery] = useState("");
  const [companyId, setCompanyId] = useState("");
  const [riskLevel, setRiskLevel] = useState("");
  const [status, setStatus] = useState("");

  const filtered = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return candidates.filter((candidate) => {
      const matchesKeyword =
        !keyword ||
        [
          candidate.name,
          candidate.company_name,
          candidate.title,
          candidate.department,
          candidate.location,
          candidate.domain
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(keyword);
      const matchesCompany = !companyId || candidate.current_company_id === companyId;
      const matchesRisk = !riskLevel || candidate.risk_level === riskLevel;
      const matchesStatus = !status || candidate.follow_status === status;
      return matchesKeyword && matchesCompany && matchesRisk && matchesStatus;
    });
  }, [candidates, companyId, query, riskLevel, status]);

  const statuses = [...new Set(candidates.map((candidate) => candidate.follow_status).filter(Boolean))];

  return (
    <div className="grid gap-4">
      <div className="tn-surface grid gap-3 rounded-lg p-4 md:grid-cols-4">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="tn-field"
          placeholder="搜索姓名、公司、岗位、方向"
        />
        <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} className="tn-field">
          <option value="">全部公司</option>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
        <select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)} className="tn-field">
          <option value="">全部风险</option>
          {Object.entries(RISK_LEVEL_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
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

      <div className="tn-surface overflow-hidden rounded-lg">
        <div className="border-b border-border px-5 py-3 text-sm font-bold text-muted-foreground">
          {filtered.length} / {candidates.length} 位人才
        </div>
        <table className="tn-table">
          <thead>
            <tr>
              <th>候选人</th>
              <th>公司</th>
              <th>岗位</th>
              <th>方向</th>
              <th>风险</th>
              <th>评分</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((candidate) => (
              <tr key={candidate.id}>
                <td>
                  <Link href={`/candidates/${candidate.id}`} className="tn-link">
                    {candidate.name}
                  </Link>
                  <p className="mt-1 text-xs text-muted-foreground">{candidate.location ?? "-"}</p>
                </td>
                <td className="font-semibold">{candidate.company_name}</td>
                <td>{candidate.title}</td>
                <td>{candidate.domain ?? "-"}</td>
                <td>
                  <RiskBadge level={candidate.risk_level} />
                </td>
                <td>
                  <span className="font-black">{candidate.risk_score ?? "-"}</span>
                  <span className="text-muted-foreground"> / {candidate.confidence_score ?? "-"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createBrowserTask, type CandidateListItem, type Company } from "@/lib/api";
import { BROWSER_TASK_TYPE_LABELS, TARGET_SITE_LABELS } from "@/lib/labels";

const TASK_TYPES = ["verify_profile", "search_candidate", "search_company_signal"];
const TARGET_SITES = ["linkedin", "maimai", "search_engine", "arxiv", "company_site"];

export function BrowserTaskForm({
  candidates,
  companies
}: {
  candidates: CandidateListItem[];
  companies: Company[];
}) {
  const router = useRouter();
  const [taskType, setTaskType] = useState("verify_profile");
  const [targetSite, setTargetSite] = useState("search_engine");
  const [candidateId, setCandidateId] = useState(candidates[0]?.id ?? "");
  const [companyId, setCompanyId] = useState(candidates[0]?.current_company_id ?? "");
  const [query, setQuery] = useState("https://example.com");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await createBrowserTask({
        task_type: taskType,
        target_site: targetSite,
        query,
        candidate_id: candidateId || undefined,
        company_id: companyId || undefined
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建任务失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="tn-surface rounded-lg p-5" onSubmit={onSubmit}>
      <div className="mb-4">
        <h2 className="font-black">新建网页搜索任务</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          输入公开 URL 或搜索关键词。后端会尝试用 Playwright 读取页面，并生成待确认草稿。
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <select value={taskType} onChange={(event) => setTaskType(event.target.value)} className="tn-field">
          {TASK_TYPES.map((item) => (
            <option key={item} value={item}>
              {BROWSER_TASK_TYPE_LABELS[item]}
            </option>
          ))}
        </select>
        <select value={targetSite} onChange={(event) => setTargetSite(event.target.value)} className="tn-field">
          {TARGET_SITES.map((item) => (
            <option key={item} value={item}>
              {TARGET_SITE_LABELS[item]}
            </option>
          ))}
        </select>
        <select
          value={candidateId}
          onChange={(event) => {
            setCandidateId(event.target.value);
            const candidate = candidates.find((item) => item.id === event.target.value);
            if (candidate) setCompanyId(candidate.current_company_id);
          }}
          className="tn-field"
        >
          <option value="">不绑定候选人</option>
          {candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.name} / {candidate.company_name}
            </option>
          ))}
        </select>
        <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} className="tn-field">
          <option value="">不绑定公司</option>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      </div>
      <textarea
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        rows={3}
        className="tn-field mt-3"
        placeholder="输入公开 URL、搜索关键词或验证任务"
        required
      />
      <div className="mt-3 flex items-center justify-between gap-3">
        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting} className="tn-button tn-button-primary">
          <Search className="h-4 w-4" />
          {isSubmitting ? "执行中" : "创建并执行"}
        </button>
      </div>
    </form>
  );
}

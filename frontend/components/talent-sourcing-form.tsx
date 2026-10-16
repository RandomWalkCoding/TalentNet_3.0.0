"use client";

import { ExternalLink, Save, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  addBrowserTaskResultToPool,
  runTalentSourcing,
  saveCandidateLead,
  type BrowserTask,
  type Company,
  type TalentSourcingResponse
} from "@/lib/api";

const LEAD_PAGE_SIZE = 20;

export function TalentSourcingForm({
  companies,
  onTasksCreated
}: {
  companies: Company[];
  onTasksCreated?: (tasks: BrowserTask[]) => void;
}) {
  const router = useRouter();
  const [talentProfile, setTalentProfile] = useState(
    "帮我检索 LinkedIn 公开页面，找到 Claude / Anthropic 的技术人员，重点关注 AI infra、LLM inference、research engineer"
  );
  const [companyId, setCompanyId] = useState("");
  const [targetCount, setTargetCount] = useState(5);
  const [publicSiteScope, setPublicSiteScope] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<TalentSourcingResponse | null>(null);
  const [hiddenLeadKeys, setHiddenLeadKeys] = useState<Set<string>>(new Set());
  const [selectedLeadKeys, setSelectedLeadKeys] = useState<Set<string>>(new Set());
  const [leadPage, setLeadPage] = useState(1);
  const [savingLeadKey, setSavingLeadKey] = useState("");
  const [batchMessage, setBatchMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const leadEntries =
    result?.extracted_candidates.map((lead, index) => ({
      lead,
      index,
      key: leadKey(lead, index)
    })) ?? [];
  const visibleLeadEntries = leadEntries.filter((entry) => !hiddenLeadKeys.has(entry.key));
  const totalLeadPages = Math.max(1, Math.ceil(visibleLeadEntries.length / LEAD_PAGE_SIZE));
  const currentLeadPage = Math.min(leadPage, totalLeadPages);
  const pagedLeadEntries = visibleLeadEntries.slice(
    (currentLeadPage - 1) * LEAD_PAGE_SIZE,
    currentLeadPage * LEAD_PAGE_SIZE
  );
  const allLeadPageSelected =
    pagedLeadEntries.length > 0 && pagedLeadEntries.every((entry) => selectedLeadKeys.has(entry.key));

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    setResult(null);
    setHiddenLeadKeys(new Set());
    setSelectedLeadKeys(new Set());
    setLeadPage(1);
    setBatchMessage(null);
    try {
      const response = await runTalentSourcing({
        talent_profile: talentProfile,
        company_id: companyId || null,
        target_count: targetCount,
        public_site_scope: publicSiteScope || null
      });
      setResult(response);
      onTasksCreated?.(response.tasks);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI 检索候选人失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function saveLead(taskId: string | null, key: string) {
    if (savingLeadKey) return;
    const entry = leadEntries.find((item) => item.key === key);
    const lead = entry?.lead;
    if (!lead?.full_name) {
      setError("缺少候选人姓名，无法存储");
      return;
    }
    setSavingLeadKey(key);
    try {
      if (taskId) {
        await addBrowserTaskResultToPool(taskId);
      } else {
        await saveCandidateLead({
          full_name: lead.full_name,
          current_company: lead.current_company,
          title: lead.title,
          education: lead.education,
          profile_links: lead.profile_links,
          source_snippet: lead.source_snippet,
          confidence: lead.confidence
        });
      }
      hideLead(key);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "存储候选人失败");
    } finally {
      setSavingLeadKey("");
    }
  }

  function hideLead(key: string) {
    setHiddenLeadKeys((current) => new Set(current).add(key));
    setSelectedLeadKeys((current) => {
      const next = new Set(current);
      next.delete(key);
      return next;
    });
  }

  function toggleLeadSelected(key: string) {
    setSelectedLeadKeys((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleLeadPageSelected() {
    setSelectedLeadKeys((current) => {
      const next = new Set(current);
      if (allLeadPageSelected) pagedLeadEntries.forEach((entry) => next.delete(entry.key));
      else pagedLeadEntries.forEach((entry) => next.add(entry.key));
      return next;
    });
  }

  async function saveSelectedLeads() {
    if (savingLeadKey) return;
    const selected = visibleLeadEntries.filter((entry) => selectedLeadKeys.has(entry.key));
    if (!selected.length) return;
    setBatchMessage("批量存储中...");
    let success = 0;
    for (const entry of selected) {
      if (!entry.lead.full_name) continue;
      setSavingLeadKey(entry.key);
      try {
        if (entry.lead.task_id) {
          await addBrowserTaskResultToPool(entry.lead.task_id);
        } else {
          await saveCandidateLead({
            full_name: entry.lead.full_name,
            current_company: entry.lead.current_company,
            title: entry.lead.title,
            education: entry.lead.education,
            profile_links: entry.lead.profile_links,
            source_snippet: entry.lead.source_snippet,
            confidence: entry.lead.confidence
          });
        }
        hideLead(entry.key);
        success += 1;
      } catch {
        // Keep failed items visible so the user can retry or inspect them.
      }
    }
    setSavingLeadKey("");
    setBatchMessage(`已存储 ${success}/${selected.length} 条`);
    router.refresh();
  }

  function ignoreSelectedLeads() {
    const count = selectedLeadKeys.size;
    selectedLeadKeys.forEach((key) => hideLead(key));
    setBatchMessage(`已忽略 ${count} 条`);
  }

  return (
    <form className="tn-surface rounded-lg p-5" onSubmit={onSubmit}>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-black">AI 检索</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            直接输入自然语言任务。系统会生成检索策略，读取公开搜索结果，并把候选人结构化成可处理卡片。
          </p>
        </div>
        <Sparkles className="h-5 w-5 text-primary" />
      </div>
      <textarea
        value={talentProfile}
        onChange={(event) => setTalentProfile(event.target.value)}
        rows={4}
        className="tn-field"
        placeholder="例如：帮我检索 LinkedIn 公开页面，找到 Claude 的技术人员，重点关注 AI infra 和 research engineer"
        required
      />
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <select value={companyId} onChange={(event) => setCompanyId(event.target.value)} className="tn-field">
          <option value="">不限公司</option>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
        <label className="grid gap-1 text-xs font-bold text-muted-foreground">
          要搜索多少人
          <input
            type="number"
            min={1}
            max={200}
            value={targetCount}
            onChange={(event) => setTargetCount(Number(event.target.value))}
            className="tn-field"
          />
        </label>
        <label className="grid gap-1 text-xs font-bold text-muted-foreground">
          限定公开网页/域名
          <input
            value={publicSiteScope}
            onChange={(event) => setPublicSiteScope(event.target.value)}
            className="tn-field"
            placeholder="例如 linkedin.com/in 或 github.com"
          />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting} className="tn-button tn-button-primary">
          <Sparkles className="h-4 w-4" />
          {isSubmitting ? "检索中" : "开始 AI 检索"}
        </button>
      </div>

      {result ? (
        <div className="mt-4 grid gap-4">
          <div className="rounded-md border bg-white p-4 text-sm">
            <p className="font-black">
              已完成 {result.tasks.length} 个检索动作，提取出 {visibleLeadEntries.length} 个候选人卡片
            </p>
            <p className="mt-1 text-xs font-bold text-muted-foreground">
              模型：{result.llm_used ? `${result.model_provider} / ${result.model_name}` : "本地兜底规则"}
            </p>
            {result.query_plan.length ? (
              <div className="mt-3 grid gap-2">
                <p className="text-xs font-black text-slate-700">本次实际检索式</p>
                <div className="flex flex-wrap gap-2">
                  {result.query_plan.map((item, index) => (
                    <span key={`${item.query}-${index}`} className="rounded-md bg-muted px-2 py-1 text-xs font-semibold">
                      {item.query}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          {visibleLeadEntries.length ? (
            <div className="grid gap-3">
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-white p-3">
                <label className="flex items-center gap-2 text-sm font-bold text-slate-800">
                  <input type="checkbox" checked={allLeadPageSelected} onChange={toggleLeadPageSelected} />
                  选择本页
                </label>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold text-muted-foreground">
                    共 {visibleLeadEntries.length} 条，已选 {selectedLeadKeys.size} 条
                  </span>
                  <button
                    type="button"
                    className="tn-button tn-button-primary"
                    disabled={!selectedLeadKeys.size || Boolean(savingLeadKey)}
                    onClick={saveSelectedLeads}
                  >
                    批量存储
                  </button>
                  <button
                    type="button"
                    className="tn-button tn-button-secondary"
                    disabled={!selectedLeadKeys.size || Boolean(savingLeadKey)}
                    onClick={ignoreSelectedLeads}
                  >
                    批量忽略
                  </button>
                </div>
                {batchMessage ? <p className="w-full text-xs font-bold text-muted-foreground">{batchMessage}</p> : null}
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                {pagedLeadEntries.map(({ lead, key }) => {
                  const completeness = fieldCompleteness(lead);
                  const qualityLabel = completeness >= 3 ? "字段完整" : completeness >= 2 ? "可入库核实" : "缺字段";
                  return (
                  <article key={key} className="rounded-lg border bg-white p-4 shadow-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex min-w-0 gap-3">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={selectedLeadKeys.has(key)}
                          onChange={() => toggleLeadSelected(key)}
                          aria-label={`选择 ${lead.full_name || "未识别姓名"}`}
                        />
                        <div className="min-w-0">
                          <p className="text-[11px] font-black uppercase tracking-wide text-muted-foreground">姓名</p>
                          <h3 className="text-lg font-black">{lead.full_name || "未识别姓名"}</h3>
                          <CandidateFacts
                            company={lead.current_company}
                            title={lead.title}
                            education={lead.education}
                          />
                        </div>
                      </div>
                      <div className="grid justify-items-end gap-1">
                        <span className="rounded-md bg-muted px-2 py-1 text-xs font-black text-muted-foreground">
                          {Math.round((lead.confidence ?? 0) * 100)}%
                        </span>
                        <span className="rounded-md bg-primary/10 px-2 py-1 text-xs font-black text-primary">
                          {qualityLabel} {completeness}/3
                        </span>
                      </div>
                    </div>
                    {lead.source_snippet ? (
                      <p className="mt-3 line-clamp-3 text-sm leading-6 text-muted-foreground">
                        {compactSnippet(lead.source_snippet, lead.full_name)}
                      </p>
                    ) : null}
                    {lead.evidence ? (
                      <p className="mt-2 rounded-md bg-muted/60 px-3 py-2 text-xs font-semibold leading-5 text-slate-700">
                        证据说明：{lead.evidence}
                      </p>
                    ) : null}
                    {lead.query ? (
                      <p className="mt-2 text-xs font-semibold text-muted-foreground">检索式：{lead.query}</p>
                    ) : null}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {lead.profile_links.slice(0, 2).map((link) => (
                        <a key={link} href={link} target="_blank" rel="noreferrer" className="tn-button tn-button-secondary">
                          <ExternalLink className="h-4 w-4" />
                          来源
                        </a>
                      ))}
                      <button
                        type="button"
                        className="tn-button tn-button-primary"
                        disabled={!lead.full_name || savingLeadKey === key}
                        onClick={() => saveLead(lead.task_id, key)}
                      >
                        <Save className="h-4 w-4" />
                        {savingLeadKey === key ? "加入中" : "加入人才猎场"}
                      </button>
                      <button type="button" className="tn-button tn-button-secondary" onClick={() => hideLead(key)}>
                        <X className="h-4 w-4" />
                        忽略
                      </button>
                    </div>
                  </article>
                  );
                })}
              </div>

              {visibleLeadEntries.length > LEAD_PAGE_SIZE ? (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-white p-3">
                  <p className="text-xs font-bold text-muted-foreground">
                    第 {currentLeadPage} / {totalLeadPages} 页，每页 {LEAD_PAGE_SIZE} 条
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="tn-button tn-button-secondary"
                      disabled={currentLeadPage <= 1}
                      onClick={() => setLeadPage((value) => Math.max(1, value - 1))}
                    >
                      上一页
                    </button>
                    <button
                      type="button"
                      className="tn-button tn-button-secondary"
                      disabled={currentLeadPage >= totalLeadPages}
                      onClick={() => setLeadPage((value) => Math.min(totalLeadPages, value + 1))}
                    >
                      下一页
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="rounded-md border bg-white p-4 text-sm text-muted-foreground">
              这次没有提取出清晰的候选人卡片。可以换一个更具体的公司、岗位或来源范围重新检索。
            </div>
          )}
        </div>
      ) : null}
    </form>
  );
}

function CandidateFacts({
  company,
  title,
  education
}: {
  company: string | null;
  title: string | null;
  education: string | null;
}) {
  const facts = [
    ["公司", company],
    ["职位", title],
    ["毕业院校", education]
  ];
  return (
    <dl className="mt-3 grid gap-2 text-sm md:grid-cols-3">
      {facts.map(([label, value]) => (
        <div key={label} className="rounded-md bg-muted/60 px-3 py-2">
          <dt className="text-[11px] font-black text-muted-foreground">{label}</dt>
          <dd className="mt-1 font-semibold text-slate-800">{value || "未提取到"}</dd>
        </div>
      ))}
    </dl>
  );
}

function compactSnippet(snippet: string, name: string | null) {
  let value = snippet.replace(/\s+/g, " ").trim();
  if (name) {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    value = value.replace(new RegExp(`^(?:${escaped}\\s*(?:-|:|,)?\\s*)+`, "i"), "");
  }
  return value || snippet;
}

function fieldCompleteness(lead: TalentSourcingResponse["extracted_candidates"][number]) {
  return [lead.full_name, lead.current_company, lead.title].filter(Boolean).length;
}

function leadKey(lead: TalentSourcingResponse["extracted_candidates"][number], index: number) {
  return `${lead.full_name ?? "unknown"}-${lead.profile_links[0] ?? lead.task_id ?? index}`;
}

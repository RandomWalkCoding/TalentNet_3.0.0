"use client";

import { CheckCircle2, ExternalLink, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { confirmBrowserTaskEvidence, runTalentSourcing, type BrowserTask } from "@/lib/api";

export function CandidateLatestSearchPanel({
  candidateId,
  companyId,
  candidateName,
  title,
  companyName
}: {
  candidateId: string;
  companyId: string;
  candidateName: string;
  title: string;
  companyName: string;
}) {
  const router = useRouter();
  const [siteScope, setSiteScope] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [savingTaskId, setSavingTaskId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<BrowserTask[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function searchLatest() {
    if (isSearching) return;
    setIsSearching(true);
    setError(null);
    setMessage(null);
    try {
      const response = await runTalentSourcing({
        candidate_id: candidateId,
        company_id: companyId,
        target_count: 6,
        public_site_scope: siteScope || null,
        talent_profile: `${candidateName}, ${title}, ${companyName}, latest role change public signals`
      });
      setTasks(response.tasks);
      setMessage(`已完成 ${response.tasks.length} 条网页搜索，逐条确认后才会写入数据库。`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "搜索失败");
    } finally {
      setIsSearching(false);
    }
  }

  async function saveTask(taskId: string) {
    setSavingTaskId(taskId);
    setError(null);
    try {
      await confirmBrowserTaskEvidence(taskId);
      setTasks((current) => current.filter((task) => task.id !== taskId));
      setMessage("已保存为候选人证据，并同步进入共享数据库。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSavingTaskId(null);
    }
  }

  return (
    <section className="tn-surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-black">一键 AI 搜索候选人最新情况</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            系统会自动操纵网页搜索公开页面和已授权数据源。结果不会自动入库，需要逐条判断是否保存。
          </p>
        </div>
        <button type="button" onClick={searchLatest} disabled={isSearching} className="tn-button tn-button-primary">
          <Search className="h-4 w-4" />
          {isSearching ? "搜索中" : "开始搜索"}
        </button>
      </div>

      <label className="mt-4 grid gap-1 text-xs font-bold text-muted-foreground">
        限定公开网页/域名
        <input
          value={siteScope}
          onChange={(event) => setSiteScope(event.target.value)}
          className="tn-field"
          placeholder="例如 linkedin.com/in、github.com、某公司官网"
        />
      </label>

      {message ? <p className="mt-3 text-sm font-semibold text-emerald-700">{message}</p> : null}
      {error ? <p className="mt-3 text-sm font-semibold text-red-700">{error}</p> : null}

      {tasks.length ? (
        <div className="mt-4 grid gap-3">
          {tasks.map((task) => (
            <article key={task.id} className="rounded-md border bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black text-muted-foreground">{task.target_site}</p>
                  <h3 className="mt-1 font-black">{task.evidence_draft?.title ?? task.page_title ?? task.query}</h3>
                </div>
                <span className="rounded-md bg-muted px-2 py-1 text-xs font-black">{task.status}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">
                {task.evidence_draft?.summary ?? task.result_summary ?? task.query}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {task.page_url ? (
                  <a href={task.page_url} target="_blank" rel="noreferrer" className="tn-button tn-button-secondary">
                    <ExternalLink className="h-4 w-4" />
                    打开来源
                  </a>
                ) : null}
                {task.evidence_draft ? (
                  <button
                    type="button"
                    onClick={() => saveTask(task.id)}
                    disabled={savingTaskId === task.id}
                    className="tn-button tn-button-primary"
                  >
                    <CheckCircle2 className="h-4 w-4" />
                    {savingTaskId === task.id ? "保存中" : "确认保存"}
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

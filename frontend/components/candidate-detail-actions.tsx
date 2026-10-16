"use client";

import { CheckCircle2, ExternalLink, FileUp, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  confirmBrowserTaskEvidence,
  createBrowserTask,
  uploadEvidenceDocument,
  type BrowserTask
} from "@/lib/api";

type CandidateDetailActionsProps = {
  candidateId: string;
  companyId: string;
  candidateName: string;
  title: string;
  companyName: string;
};

export function CandidateDetailActions({
  candidateId,
  companyId,
  candidateName,
  title,
  companyName
}: CandidateDetailActionsProps) {
  const router = useRouter();
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
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
      const task = await createBrowserTask({
        task_type: "candidate_update",
        candidate_id: candidateId,
        company_id: companyId,
        target_site: "search_engine",
        query: `${candidateName} ${title} ${companyName} latest role change public signals`
      });
      setTasks([task]);
      setMessage(task.status === "waiting_user" ? "请打开来源核对草稿，再决定是否保存。" : "网页读取未完成；请查看任务状态后重试或手动添加证据。");
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
      setMessage("已保存为候选人证据。");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSavingTaskId(null);
    }
  }

  async function uploadDocument(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || isUploading) return;
    setIsUploading(true);
    setError(null);
    setMessage(null);
    try {
      const result = await uploadEvidenceDocument({
        candidateId,
        companyId,
        file,
        confirmedByUser: true
      });
      setMessage(`已读取 ${result.extracted_characters} 个字符，并生成证据：${result.evidence.title}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传文件失败");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="mt-4 grid gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <button type="button" onClick={searchLatest} disabled={isSearching} className="tn-button tn-button-primary">
          <Search className="h-4 w-4" />
          {isSearching ? "搜索中" : "公开网页核查"}
        </button>
        <label className="tn-button tn-button-secondary w-fit">
          <FileUp className="h-4 w-4" />
          {isUploading ? "上传中" : "手动上传"}
          <input type="file" accept=".txt,.md,.csv,.pdf,.docx,.xlsx,.json,.html,.htm" onChange={uploadDocument} className="hidden" />
        </label>
      </div>

      {message ? <p className="text-sm font-semibold text-emerald-700">{message}</p> : null}
      {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}

      {tasks.length ? (
        <div className="grid gap-2 rounded-md border bg-white p-3">
          {tasks.map((task) => (
            <article key={task.id} className="rounded-md bg-muted/45 p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-bold text-muted-foreground">{task.target_site}</p>
                  <p className="text-xs font-bold text-muted-foreground">{task.status === "waiting_user" ? "待确认" : task.status === "failed" ? "读取失败" : task.status}</p>
                  <h3 className="mt-1 truncate font-black">{task.evidence_draft?.title ?? task.page_title ?? task.query}</h3>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-700">
                    {task.evidence_draft?.summary ?? task.result_summary ?? task.query}
                  </p>
                </div>
                <div className="flex shrink-0 flex-wrap gap-2">
                  {task.page_url ? (
                    <a href={task.page_url} target="_blank" rel="noreferrer" className="tn-button tn-button-secondary">
                      <ExternalLink className="h-4 w-4" />
                      来源
                    </a>
                  ) : null}
                  {task.status === "waiting_user" && task.evidence_draft ? (
                    <button
                      type="button"
                      onClick={() => saveTask(task.id)}
                      disabled={savingTaskId === task.id}
                      className="tn-button tn-button-primary"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      {savingTaskId === task.id ? "保存中" : "保存"}
                    </button>
                  ) : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </div>
  );
}

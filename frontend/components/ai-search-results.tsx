"use client";

import { ChevronDown, ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { useMemo, useState } from "react";

import { TalentSourcingForm } from "@/components/talent-sourcing-form";
import {
  addBrowserTaskResultToPool,
  cancelBrowserTask,
  retryBrowserTask,
  type BrowserTask,
  type Company
} from "@/lib/api";

const PAGE_SIZE = 20;
const HIDDEN_STATUSES = new Set(["completed", "cancelled", "failed"]);

const SOURCE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  maimai: "脉脉",
  search_engine: "公开网页",
  company_site: "公司官网",
  job_site: "招聘页面",
  arxiv: "论文/研究",
  patent: "专利"
};

export function AISearchResults({ companies }: { companies: Company[] }) {
  const [hasSearched, setHasSearched] = useState(false);
  const [localTasks, setLocalTasks] = useState<BrowserTask[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [openId, setOpenId] = useState("");
  const [page, setPage] = useState(1);
  const [workingIds, setWorkingIds] = useState<Set<string>>(new Set());
  const [batchMessage, setBatchMessage] = useState<string | null>(null);

  const visible = useMemo(
    () => localTasks.filter((task) => !HIDDEN_STATUSES.has(task.status)),
    [localTasks]
  );
  const totalPages = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = visible.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);
  const allPageSelected = paged.length > 0 && paged.every((task) => selectedIds.has(task.id));

  function addCreatedTasks(tasks: BrowserTask[]) {
    setHasSearched(true);
    setLocalTasks(tasks.filter((task) => !HIDDEN_STATUSES.has(task.status)));
    setSelectedIds(new Set());
    setOpenId("");
    setPage(1);
    setWorkingIds(new Set());
    setBatchMessage(null);
  }

  function hideTask(taskId: string) {
    setLocalTasks((current) => current.filter((item) => item.id !== taskId));
    setSelectedIds((current) => {
      const next = new Set(current);
      next.delete(taskId);
      return next;
    });
  }

  function toggleSelected(taskId: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  }

  function togglePageSelected() {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (allPageSelected) paged.forEach((task) => next.delete(task.id));
      else paged.forEach((task) => next.add(task.id));
      return next;
    });
  }

  async function runTaskAction(task: BrowserTask, action: "add" | "skip" | "retry", silent = false) {
    if (workingIds.has(task.id)) return false;
    setWorkingIds((current) => new Set(current).add(task.id));
    if (!silent) setBatchMessage(null);
    try {
      if (action === "add") {
        if (!canAdd(task)) return false;
        await addBrowserTaskResultToPool(task.id);
        hideTask(task.id);
      }
      if (action === "skip") {
        await cancelBrowserTask(task.id);
        hideTask(task.id);
      }
      if (action === "retry") {
        const retried = await retryBrowserTask(task.id);
        if (HIDDEN_STATUSES.has(retried.status)) hideTask(task.id);
        else setLocalTasks((current) => current.map((item) => (item.id === task.id ? retried : item)));
      }
      return true;
    } catch (err) {
      if (!silent) setBatchMessage(err instanceof Error ? err.message : "处理失败");
      return false;
    } finally {
      setWorkingIds((current) => {
        const next = new Set(current);
        next.delete(task.id);
        return next;
      });
    }
  }

  async function runBatch(action: "add" | "skip" | "retry") {
    const tasks = visible.filter((task) => selectedIds.has(task.id));
    if (!tasks.length) return;
    setBatchMessage("批量处理中...");
    let success = 0;
    for (const task of tasks) {
      const done = await runTaskAction(task, action, true);
      if (done) success += 1;
    }
    setBatchMessage(`已处理 ${success}/${tasks.length} 条`);
  }

  return (
    <div className="grid gap-4">
      <TalentSourcingForm companies={companies} onTasksCreated={addCreatedTasks} />

      <section className="tn-surface rounded-lg">
        <div className="tn-section-bar">
          <div>
            <h2 className="font-black">待判断候选线索</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              首次打开为空。这里只显示本轮 AI 检索产生、尚未处理的线索；失败、已跳过和已入库条目不会出现在这里。
            </p>
          </div>
          <span className="rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
            共 {visible.length} 条
          </span>
        </div>

        {visible.length > 0 ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-3">
            <label className="flex items-center gap-2 text-sm font-bold">
              <input type="checkbox" checked={allPageSelected} onChange={togglePageSelected} />
              选择本页
            </label>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-muted-foreground">已选 {selectedIds.size} 条</span>
              <button type="button" className="tn-button tn-button-primary" disabled={!selectedIds.size} onClick={() => runBatch("add")}>
                批量加入猎场
              </button>
              <button type="button" className="tn-button tn-button-secondary" disabled={!selectedIds.size} onClick={() => runBatch("skip")}>
                批量跳过
              </button>
              <button type="button" className="tn-button tn-button-secondary" disabled={!selectedIds.size} onClick={() => runBatch("retry")}>
                批量重试
              </button>
            </div>
            {batchMessage ? <p className="w-full text-xs font-bold text-muted-foreground">{batchMessage}</p> : null}
          </div>
        ) : null}

        <div className="divide-y divide-border">
          {paged.map((task) => {
            const isOpen = openId === task.id;
            const clue = clueSummary(task);
            const isWorking = workingIds.has(task.id);
            return (
              <article key={task.id}>
                <div className="grid gap-3 px-5 py-4 md:grid-cols-[auto_minmax(0,1fr)_auto] md:items-start">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selectedIds.has(task.id)}
                    onChange={() => toggleSelected(task.id)}
                    aria-label={`选择 ${clue.title}`}
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-black">{clue.title}</p>
                      <span className="rounded-md bg-muted px-2 py-1 text-xs font-black">{statusLabel(task.status)}</span>
                      <span className="rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
                        {clue.source}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">{clue.oneLine}</p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 md:justify-end">
                    {task.page_url ? (
                      <a href={task.page_url} target="_blank" rel="noreferrer" className="tn-button tn-button-secondary">
                        <ExternalLink className="h-4 w-4" />
                        来源
                      </a>
                    ) : null}
                    {canAdd(task) ? (
                      <button type="button" className="tn-button tn-button-primary" disabled={isWorking} onClick={() => runTaskAction(task, "add")}>
                        加入猎场
                      </button>
                    ) : null}
                    <button type="button" className="tn-button tn-button-secondary" disabled={isWorking} onClick={() => runTaskAction(task, "retry")}>
                      重试
                    </button>
                    <button type="button" className="tn-button tn-button-secondary" disabled={isWorking} onClick={() => runTaskAction(task, "skip")}>
                      跳过
                    </button>
                    <button type="button" className="tn-button tn-button-secondary" onClick={() => setOpenId(isOpen ? "" : task.id)}>
                      <ChevronDown className={`h-4 w-4 transition ${isOpen ? "rotate-180" : ""}`} />
                      详情
                    </button>
                  </div>
                </div>

                {isOpen ? (
                  <div className="bg-muted/35 px-5 pb-5">
                    <div className="grid gap-4 rounded-lg border bg-white p-4">
                      <div className="grid gap-3 md:grid-cols-3">
                        <Insight label="发现了什么" value={clue.finding} strong />
                        <Insight label="为什么相关" value={clue.relevance} />
                        <Insight label="下一步" value={clue.nextStep} />
                      </div>
                      <div className="rounded-md bg-muted/45 p-3">
                        <p className="text-xs font-bold text-muted-foreground">原始检索</p>
                        <p className="mt-1 text-sm leading-6 text-slate-700">{task.query}</p>
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}

          {visible.length === 0 ? (
            <div className="p-5">
              <div className="rounded-md border bg-white p-6 text-sm text-muted-foreground">
                {hasSearched
                  ? "本轮没有可处理的待判断线索。失败、已跳过和已入库条目不会显示在这里。"
                  : "暂无待判断线索。开始一次新的 AI 检索后，本轮需要处理的线索才会显示在这里。"}
              </div>
            </div>
          ) : null}
        </div>

        {visible.length > PAGE_SIZE ? (
          <div className="flex flex-wrap items-center justify-between gap-3 border-t px-5 py-3">
            <p className="text-xs font-bold text-muted-foreground">
              第 {currentPage} / {totalPages} 页，每页 {PAGE_SIZE} 条
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="tn-button tn-button-secondary"
                disabled={currentPage <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                上一页
              </button>
              <button
                type="button"
                className="tn-button tn-button-secondary"
                disabled={currentPage >= totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                下一页
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function canAdd(task: BrowserTask) {
  return Boolean(task.evidence_draft?.candidate_id) && task.status === "waiting_user";
}

function Insight({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="rounded-md border bg-white p-3">
      <p className="text-xs font-bold text-muted-foreground">{label}</p>
      <p className={`mt-2 text-sm leading-6 ${strong ? "font-semibold text-slate-900" : "text-slate-700"}`}>{value}</p>
    </div>
  );
}

function clueSummary(task: BrowserTask) {
  const title = readableTitle(task);
  const summary = cleanSummary(task.evidence_draft?.summary ?? task.result_summary ?? "");
  const source = SOURCE_LABELS[task.target_site] ?? task.target_site;
  return {
    title,
    source,
    oneLine: summary || task.query,
    finding: summary || "已生成一条待判断的公开页面线索，展开后可核实具体内容。",
    relevance: relevanceFromTask(task),
    nextStep: task.evidence_draft?.candidate_id
      ? "已归属到候选人，可直接加入猎场。"
      : "判断是否对应真实候选人，再归入人才库或跳过。"
  };
}

function readableTitle(task: BrowserTask) {
  const raw = task.evidence_draft?.title ?? task.page_title ?? task.query;
  return raw.replace(/^待核实网页任务[:：]\s*/, "").replace(/^候选线索[:：]\s*/, "").slice(0, 120);
}

function cleanSummary(value: string) {
  return value
    .replace(/^网页可见文本摘要[:：]\s*/, "")
    .replace(/^后端已尝试执行真实浏览器任务，但当前环境未能完成页面读取。/, "页面读取未完成。")
    .slice(0, 220);
}

function relevanceFromTask(task: BrowserTask) {
  const query = task.query.replace(/\s+/g, " ").trim();
  if (task.target_site === "linkedin" || task.target_site === "maimai") {
    return "可能包含履历、岗位或职业状态变化，适合判断是否值得纳入候选人跟进。";
  }
  if (task.target_site === "company_site") {
    return "可能来自公司官网或团队页面，可用于确认当前组织、岗位和项目背景。";
  }
  if (task.target_site === "arxiv" || task.target_site === "patent") {
    return "可能体现研究、专利或技术方向，适合验证候选人与人才画像的匹配度。";
  }
  if (task.target_site === "job_site") {
    return "可能反映团队扩张、岗位开放或组织变化，可作为流动信号的旁证。";
  }
  return query ? `与本次人才画像相关：${query.slice(0, 90)}` : "与本次人才画像相关，需要结合来源页面确认。";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    waiting_user: "待判断",
    completed: "已入库",
    cancelled: "已跳过",
    failed: "失败",
    running: "搜索中",
    pending: "排队中"
  };
  return labels[status] ?? status;
}

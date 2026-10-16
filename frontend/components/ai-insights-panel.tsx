"use client";

import { Brain, Copy, LoaderCircle, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import {
  generateOutreach,
  generateSummary,
  getLLMStatus,
  recordUsageEvent,
  type AISummary,
  type LLMStatus,
  type OutreachResponse
} from "@/lib/api";

export function AIInsightsPanel({ candidateId }: { candidateId: string }) {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [summary, setSummary] = useState<AISummary | null>(null);
  const [outreach, setOutreach] = useState<OutreachResponse | null>(null);
  const [editableMessages, setEditableMessages] = useState<Record<number, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isStatusLoading, setIsStatusLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  useEffect(() => {
    recordUsageEvent(candidateId, "candidate_view").catch(() => undefined);
  }, [candidateId]);

  useEffect(() => {
    let isMounted = true;
    getLLMStatus()
      .then((payload) => {
        if (isMounted) setStatus(payload);
      })
      .catch(() => {
        if (isMounted) setStatus(null);
      })
      .finally(() => {
        if (isMounted) setIsStatusLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  async function onGenerate() {
    if (isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      const [summaryResult, outreachResult] = await Promise.all([
        generateSummary(candidateId),
        generateOutreach(candidateId)
      ]);
      setSummary(summaryResult);
      setOutreach(outreachResult);
      setEditableMessages(
        Object.fromEntries(
          outreachResult.variants.map((variant, index) => [index, variant.message])
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function copyMessage(index: number) {
    const message = editableMessages[index] ?? "";
    try {
      await navigator.clipboard.writeText(message);
      setCopiedIndex(index);
      recordUsageEvent(candidateId, "outreach_copy").catch(() => undefined);
    } catch {
      setCopiedIndex(null);
    }
  }

  const runtime = summary ?? outreach;
  const usedFallback = Boolean(runtime?.used_fallback);

  return (
    <div className="tn-surface rounded-lg">
      <div className="grid gap-4 border-b border-border px-5 py-4 md:grid-cols-[1fr_auto]">
        <div>
          <h2 className="font-black">AI 时机诊断</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            后端 LLM Gateway 生成结构化解释和可编辑开场白；前端不持有 API Key，也不计算评分。
          </p>
        </div>
        <button type="button" onClick={onGenerate} disabled={isLoading} className="tn-button tn-button-primary">
          {isLoading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
          {isLoading ? "生成中" : "生成建议"}
        </button>
      </div>

      <div className="grid gap-4 p-5">
        <div className="grid gap-3 rounded-md border bg-muted/40 p-4 md:grid-cols-[1fr_auto] md:items-center">
          <div>
            <p className="flex items-center gap-2 text-sm font-black">
              <ShieldCheck className="h-4 w-4" />
              模型状态
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {isStatusLoading
                ? "正在读取后端模型配置..."
                : status?.configured
                  ? `${status.provider} / ${status.model}`
                  : `未配置真实模型，自动使用 ${status?.fallback_model ?? "local-structured-v1"} 降级。`}
            </p>
          </div>
          <span
            className={`w-fit rounded-md px-2 py-1 text-xs font-black ${
              status?.configured ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
            }`}
          >
            {status?.configured ? "真实 LLM" : "本地降级"}
          </span>
        </div>

        {runtime ? (
          <div
            className={`rounded-md border p-3 text-sm font-semibold ${
              usedFallback
                ? "border-amber-200 bg-amber-50 text-amber-950"
                : "border-emerald-200 bg-emerald-50 text-emerald-950"
            }`}
          >
            本次使用 {runtime.model_provider} / {runtime.model_name}
            {usedFallback ? "，真实模型不可用或未配置，已安全降级。" : "，输出已通过证据引用校验。"}
          </div>
        ) : null}

        {error ? (
          <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
            {error}
          </div>
        ) : null}

        {summary ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border bg-muted/40 p-4">
              <p className="font-black">证据摘要</p>
              <p className="mt-2 text-sm leading-7">{summary.summary}</p>
            </div>
            <div className="rounded-md border bg-muted/40 p-4">
              <p className="font-black">风险解释</p>
              <p className="mt-2 text-sm leading-7">{summary.risk_explanation}</p>
            </div>
          </div>
        ) : (
          <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            点击生成建议后，后端会返回摘要、风险解释和 3 个可编辑触达话术。所有 AI 输出必须引用当前候选人的证据。
          </p>
        )}

        {summary?.cited_evidence_ids.length ? (
          <div className="flex flex-wrap gap-2">
            {summary.cited_evidence_ids.map((id) => (
              <span key={id} className="rounded-md border bg-white px-2 py-1 text-xs font-bold">
                引用 {id}
              </span>
            ))}
          </div>
        ) : null}

        {summary?.conflict_notes.length ? (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            {summary.conflict_notes.map((note) => (
              <p key={note}>{note}</p>
            ))}
          </div>
        ) : null}

        {summary?.limitations.length ? (
          <div className="rounded-md border bg-white p-4 text-sm leading-6 text-muted-foreground">
            {summary.limitations.map((item) => (
              <p key={item}>{item}</p>
            ))}
          </div>
        ) : null}

        {outreach ? (
          <div className="grid gap-4">
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-950">
              {outreach.compliance_note}
            </div>
            {outreach.variants.map((variant, index) => (
              <div key={variant.tone} className="rounded-md border bg-white p-4">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <p className="font-black">{variant.tone}</p>
                  <button
                    type="button"
                    onClick={() => copyMessage(index)}
                    className="tn-button tn-button-secondary min-h-8 px-2 py-1"
                  >
                    <Copy className="h-4 w-4" />
                    {copiedIndex === index ? "已复制" : "复制"}
                  </button>
                </div>
                <textarea
                  value={editableMessages[index] ?? variant.message}
                  onChange={(event) =>
                    setEditableMessages((current) => ({
                      ...current,
                      [index]: event.target.value
                    }))
                  }
                  rows={4}
                  className="tn-field leading-7"
                />
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                  {variant.evidence_ids.map((id) => (
                    <span key={id} className="rounded-md border px-2 py-1">
                      引用 {id}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

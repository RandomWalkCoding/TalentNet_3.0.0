"use client";

import { RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { RiskBadge } from "@/components/risk-badge";
import type { CandidateScore } from "@/lib/api";
import { refreshCandidateScore } from "@/lib/api";
import { REASON_CODE_LABELS } from "@/lib/labels";

type CandidateScoreCardProps = {
  candidateId: string;
  score: CandidateScore | null;
};

export function CandidateScoreCard({ candidateId, score }: CandidateScoreCardProps) {
  const router = useRouter();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onRefresh() {
    if (isRefreshing) return;
    setIsRefreshing(true);
    setError(null);
    try {
      await refreshCandidateScore(candidateId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "刷新评分失败");
    } finally {
      setIsRefreshing(false);
    }
  }

  const snapshot = score?.input_snapshot ?? {};
  const reviewReasons = score?.limitations.filter(
    (item) => item.includes("证据") || item.includes("未确认") || item.includes("置信度")
  );

  return (
    <div className="tn-surface rounded-lg">
      <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div>
          <h2 className="font-black">风险评分</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            后端规则模型基于证据新鲜度、来源权重和人工确认状态计算。
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing}
          className="tn-button tn-button-secondary"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
          {isRefreshing ? "刷新中" : "刷新"}
        </button>
      </div>

      {score ? (
        <div className="grid gap-5 p-5">
          <div className="flex items-center justify-between gap-3">
            <RiskBadge level={score.risk_level} />
            <span className="text-xs font-bold text-muted-foreground">{score.model_version}</span>
          </div>

          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border">
            <div className="bg-white p-4">
              <p className="text-xs font-bold text-muted-foreground">风险分</p>
              <p className="mt-2 text-3xl font-black">{score.risk_score}</p>
            </div>
            <div className="bg-white p-4">
              <p className="text-xs font-bold text-muted-foreground">置信度</p>
              <p className="mt-2 text-3xl font-black">{score.confidence_score}</p>
            </div>
          </div>

          <div className="grid gap-3 rounded-md border bg-white p-4 text-sm md:grid-cols-2">
            <Metric label="证据总数" value={snapshot.evidence_count ?? 0} />
            <Metric label="已确认" value={snapshot.confirmed_count ?? 0} />
            <Metric label="待确认" value={snapshot.unconfirmed_count ?? 0} />
            <Metric label="近期证据" value={snapshot.fresh_count ?? 0} />
            <Metric label="过期证据" value={snapshot.stale_count ?? 0} />
            <Metric label="平均置信度" value={`${Math.round((snapshot.avg_confidence ?? 0) * 100)}%`} />
          </div>

          <div>
            <p className="text-xs font-bold text-muted-foreground">推荐窗口</p>
            <p className="mt-1 font-black">{score.recommended_window}</p>
          </div>

          <div>
            <p className="text-xs font-bold text-muted-foreground">原因代码</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {score.reason_codes.length > 0 ? (
                score.reason_codes.map((code) => (
                  <span key={code} className="rounded-md border bg-white px-2 py-1 text-xs font-bold">
                    {REASON_CODE_LABELS[code] ?? code}
                  </span>
                ))
              ) : (
                <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-bold text-amber-900">
                  证据不足
                </span>
              )}
            </div>
          </div>

          {snapshot.features?.length ? (
            <div className="rounded-md border bg-white p-4">
              <p className="text-xs font-bold text-muted-foreground">评分输入摘要</p>
              <div className="mt-3 grid gap-2">
                {snapshot.features.map((feature) => (
                  <div key={feature.code} className="rounded-md bg-muted/50 p-3 text-sm">
                    <p className="font-black">{REASON_CODE_LABELS[feature.code] ?? feature.code}</p>
                    <p className="mt-1 text-muted-foreground">{feature.summary}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      权重 {feature.weight} / 证据 {feature.evidence_ids.join(", ") || "-"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <p className="text-sm leading-7 text-slate-700">{score.explanation}</p>

          {reviewReasons?.length ? (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm leading-6 text-amber-950">
              <p className="font-black">待核实原因</p>
              {reviewReasons.map((item) => (
                <p key={item} className="mt-1">
                  {item}
                </p>
              ))}
            </div>
          ) : null}

          {score.limitations.length > 0 ? (
            <div className="rounded-md border bg-white p-3 text-sm leading-6 text-muted-foreground">
              {score.limitations.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="p-5">
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
            暂无评分。请点击刷新，由后端根据现有证据生成。
          </div>
        </div>
      )}

      {error ? <p className="px-5 pb-5 text-sm font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div>
      <p className="text-xs font-bold text-muted-foreground">{label}</p>
      <p className="mt-1 font-black">{value}</p>
    </div>
  );
}

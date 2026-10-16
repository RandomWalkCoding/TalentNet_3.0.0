"use client";

import { Check, RotateCcw, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { addBrowserTaskResultToPool, cancelBrowserTask, retryBrowserTask } from "@/lib/api";

export function SearchResultDecisionActions({
  taskId,
  canAdd,
  canCancel,
  canRetry,
  needsCandidateAssignment = false,
  onSkip
}: {
  taskId: string;
  canAdd: boolean;
  canCancel: boolean;
  canRetry: boolean;
  needsCandidateAssignment?: boolean;
  onSkip?: () => void;
}) {
  const router = useRouter();
  const [isWorking, setIsWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, success: string, fallback: string) {
    if (isWorking) return;
    setIsWorking(true);
    setMessage(null);
    try {
      await action();
      setMessage(success);
      router.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : fallback);
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {canAdd ? (
        <button
          type="button"
          onClick={() => run(() => addBrowserTaskResultToPool(taskId), "已加入人才猎场", "加入猎场失败")}
          disabled={isWorking}
          className="tn-button tn-button-primary"
        >
          <Check className="h-4 w-4" />
          加入猎场
        </button>
      ) : null}
      {needsCandidateAssignment ? (
        <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs font-black text-amber-900">
          需先归属到候选人
        </span>
      ) : null}
      {canRetry ? (
        <button
          type="button"
          onClick={() => run(() => retryBrowserTask(taskId), "已重新搜索", "重试失败")}
          disabled={isWorking}
          className="tn-button tn-button-secondary"
        >
          <RotateCcw className="h-4 w-4" />
          重试
        </button>
      ) : null}
      {canCancel ? (
        <button
          type="button"
          onClick={() =>
            run(
              async () => {
                await cancelBrowserTask(taskId);
                onSkip?.();
              },
              "已跳过",
              "跳过失败"
            )
          }
          disabled={isWorking}
          className="tn-button tn-button-secondary"
        >
          <X className="h-4 w-4" />
          {isWorking ? "处理中" : "跳过"}
        </button>
      ) : null}
      {message ? <p className="text-sm font-semibold text-muted-foreground">{message}</p> : null}
    </div>
  );
}

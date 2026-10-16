"use client";

import { Check, RotateCcw, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { cancelBrowserTask, confirmBrowserTaskEvidence, retryBrowserTask } from "@/lib/api";

export function BrowserTaskActions({
  taskId,
  canConfirm,
  canCancel,
  canRetry = false
}: {
  taskId: string;
  canConfirm: boolean;
  canCancel: boolean;
  canRetry?: boolean;
}) {
  const router = useRouter();
  const [isWorking, setIsWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<unknown>, fallback: string) {
    if (isWorking) return;
    setIsWorking(true);
    setError(null);
    try {
      await action();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : fallback);
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {canConfirm ? (
        <button
          type="button"
          onClick={() => run(() => confirmBrowserTaskEvidence(taskId), "确认证据失败")}
          disabled={isWorking}
          className="tn-button tn-button-primary"
        >
          <Check className="h-4 w-4" />
          确认入库
        </button>
      ) : null}
      {canRetry ? (
        <button
          type="button"
          onClick={() => run(() => retryBrowserTask(taskId), "重试任务失败")}
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
          onClick={() => run(() => cancelBrowserTask(taskId), "取消任务失败")}
          disabled={isWorking}
          className="tn-button tn-button-secondary"
        >
          <X className="h-4 w-4" />
          取消
        </button>
      ) : null}
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
    </div>
  );
}

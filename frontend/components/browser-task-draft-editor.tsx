"use client";

import { Check, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  confirmBrowserTaskEvidence,
  updateBrowserTaskEvidenceDraft,
  type EvidenceDraft
} from "@/lib/api";

export function BrowserTaskDraftEditor({
  taskId,
  draft
}: {
  taskId: string;
  draft: EvidenceDraft;
}) {
  const router = useRouter();
  const [title, setTitle] = useState(draft.title);
  const [url, setUrl] = useState(draft.url ?? "");
  const [summary, setSummary] = useState(draft.summary);
  const [confidence, setConfidence] = useState(draft.confidence);
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function saveDraft() {
    if (isSaving) return;
    setIsSaving(true);
    setError(null);
    try {
      await updateBrowserTaskEvidenceDraft(taskId, {
        title,
        url: url || null,
        summary,
        confidence
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存草稿失败");
    } finally {
      setIsSaving(false);
    }
  }

  async function confirmDraft() {
    if (isConfirming) return;
    setIsConfirming(true);
    setError(null);
    try {
      await updateBrowserTaskEvidenceDraft(taskId, {
        title,
        url: url || null,
        summary,
        confidence
      });
      await confirmBrowserTaskEvidence(taskId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "确认草稿失败");
    } finally {
      setIsConfirming(false);
    }
  }

  return (
    <div className="mt-4 rounded-md border border-border bg-white p-4">
      <div className="grid gap-3 md:grid-cols-[1fr_10rem]">
        <input value={title} onChange={(event) => setTitle(event.target.value)} className="tn-field" />
        <label className="grid gap-1 text-xs font-bold text-muted-foreground">
          置信度 {Math.round(confidence * 100)}%
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={confidence}
            onChange={(event) => setConfidence(Number(event.target.value))}
          />
        </label>
      </div>
      <input
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        className="tn-field mt-3"
        placeholder="来源 URL"
      />
      <textarea
        value={summary}
        onChange={(event) => setSummary(event.target.value)}
        rows={4}
        className="tn-field mt-3"
      />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button type="button" onClick={saveDraft} disabled={isSaving} className="tn-button tn-button-secondary">
          <Save className="h-4 w-4" />
          {isSaving ? "保存中" : "保存修改"}
        </button>
        <button
          type="button"
          onClick={confirmDraft}
          disabled={isConfirming}
          className="tn-button tn-button-primary"
        >
          <Check className="h-4 w-4" />
          {isConfirming ? "确认中" : "确认入库"}
        </button>
        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}
      </div>
    </div>
  );
}

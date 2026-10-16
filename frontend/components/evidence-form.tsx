"use client";

import { Check, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { confirmEvidence, createEvidence } from "@/lib/api";

const SOURCES = [
  ["manual", "人工录入"],
  ["linkedin_visible", "LinkedIn 可见页"],
  ["maimai_visible", "脉脉可见页"],
  ["company_site", "公司官网"],
  ["job_site", "招聘网站"],
  ["arxiv", "arXiv"]
];

export function EvidenceForm({
  candidateId,
  companyId
}: {
  candidateId: string;
  companyId: string;
}) {
  const router = useRouter();
  const [source, setSource] = useState("manual");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [summary, setSummary] = useState("");
  const [confidence, setConfidence] = useState(0.72);
  const [confirmNow, setConfirmNow] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const evidence = await createEvidence({
        candidate_id: candidateId,
        company_id: companyId,
        source,
        title,
        url: url || null,
        summary,
        confidence,
        confirmed_by_user: false
      });
      if (confirmNow) {
        await confirmEvidence(evidence.id);
      }
      setTitle("");
      setUrl("");
      setSummary("");
      setConfidence(0.72);
      setConfirmNow(false);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "新增证据失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="tn-surface rounded-lg p-5" onSubmit={onSubmit}>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-black">新增证据</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            先保存为待确认记录；确认后由后端刷新评分。
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[0.8fr_1.2fr]">
        <select value={source} onChange={(event) => setSource(event.target.value)} className="tn-field">
          {SOURCES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <input
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="tn-field"
          placeholder="证据标题"
          required
        />
      </div>
      <input
        value={url}
        onChange={(event) => setUrl(event.target.value)}
        className="tn-field mt-3"
        placeholder="来源 URL，可选"
      />
      <textarea
        value={summary}
        onChange={(event) => setSummary(event.target.value)}
        rows={4}
        className="tn-field mt-3"
        placeholder="证据摘要，需可追溯到公开或用户授权可见来源"
        required
      />

      <div className="mt-3 grid gap-3 md:grid-cols-[1fr_auto] md:items-center">
        <label className="grid gap-2 text-xs font-bold text-muted-foreground">
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
        <label className="flex items-center gap-2 text-sm font-bold">
          <input
            type="checkbox"
            checked={confirmNow}
            onChange={(event) => setConfirmNow(event.target.checked)}
          />
          保存后立即确认
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting} className="tn-button tn-button-primary">
          {confirmNow ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {isSubmitting ? "保存中" : confirmNow ? "保存并确认" : "保存草稿"}
        </button>
      </div>
    </form>
  );
}

export function EvidenceConfirmButton({ evidenceId }: { evidenceId: string }) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onConfirm() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await confirmEvidence(evidenceId);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "确认失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={onConfirm}
        disabled={isSubmitting}
        className="tn-button tn-button-primary"
      >
        <Check className="h-4 w-4" />
        {isSubmitting ? "确认中" : "确认并刷新评分"}
      </button>
      {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}

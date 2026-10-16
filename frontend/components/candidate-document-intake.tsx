"use client";

import { FileSearch } from "lucide-react";
import { useState } from "react";

import { extractCandidatesDocument, type ExtractedCandidateDraft } from "@/lib/api";

export function CandidateDocumentIntake() {
  const [isExtracting, setIsExtracting] = useState(false);
  const [drafts, setDrafts] = useState<ExtractedCandidateDraft[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || isExtracting) return;
    setIsExtracting(true);
    setError(null);
    setMessage(null);
    setDrafts([]);
    try {
      const result = await extractCandidatesDocument(file);
      setDrafts(result.candidates);
      setMessage(`已读取 ${result.extracted_characters} 个字符，识别 ${result.candidate_count} 条候选人线索`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "智能识别失败");
    } finally {
      setIsExtracting(false);
      event.target.value = "";
    }
  }

  return (
    <div className="tn-surface rounded-lg p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-black">智能文件识别</h2>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            文件不需要固定格式；系统会尽力从任意文本、表格、PDF、Word 或网页文本中识别候选人字段。
          </p>
        </div>
        <FileSearch className="h-5 w-5 text-primary" />
      </div>
      <label className="tn-button tn-button-secondary w-fit">
        <FileSearch className="h-4 w-4" />
        {isExtracting ? "识别中" : "上传任意格式文件"}
        <input type="file" onChange={onUpload} className="hidden" />
      </label>
      {message ? <p className="mt-3 text-sm font-semibold text-emerald-700">{message}</p> : null}
      {error ? <p className="mt-3 text-sm font-semibold text-red-700">{error}</p> : null}
      {drafts.length ? (
        <div className="mt-4 grid gap-3">
          {drafts.slice(0, 8).map((draft, index) => (
            <div key={`${draft.name}-${index}`} className="rounded-md border bg-white p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-black">{draft.name ?? "未识别姓名"}</p>
                <span className="rounded-md bg-muted px-2 py-1 text-xs font-bold">
                  {Math.round(draft.confidence * 100)}%
                </span>
              </div>
              <p className="mt-1 text-muted-foreground">
                {draft.company_name ?? "未知公司"} / {draft.title ?? "未知岗位"} / {draft.domain ?? "未知方向"}
              </p>
              <p className="mt-2 leading-6">{draft.profile_summary}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

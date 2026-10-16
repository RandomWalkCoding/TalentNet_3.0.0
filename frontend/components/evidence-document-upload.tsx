"use client";

import { FileUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { uploadEvidenceDocument } from "@/lib/api";

export function EvidenceDocumentUpload({
  candidateId,
  companyId
}: {
  candidateId: string;
  companyId: string;
}) {
  const router = useRouter();
  const [confirmNow, setConfirmNow] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onUpload(event: React.ChangeEvent<HTMLInputElement>) {
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
        confirmedByUser: confirmNow
      });
      setMessage(`已读取 ${result.extracted_characters} 个字符，生成证据：${result.evidence.title}`);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "上传文件失败");
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  }

  return (
    <div className="tn-surface rounded-lg p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-black">手动上传</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            支持任意格式文件。系统会尽力读取文本、识别字段，并生成可追溯证据。
          </p>
        </div>
        <FileUp className="h-5 w-5 text-primary" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="tn-button tn-button-secondary w-fit">
          <FileUp className="h-4 w-4" />
          {isUploading ? "上传中" : "选择文件"}
          <input type="file" onChange={onUpload} className="hidden" />
        </label>
        <label className="flex items-center gap-2 text-sm font-bold">
          <input
            type="checkbox"
            checked={confirmNow}
            onChange={(event) => setConfirmNow(event.target.checked)}
          />
          上传后立即确认并刷新评分
        </label>
      </div>

      {message ? <p className="mt-3 text-sm font-semibold text-emerald-700">{message}</p> : null}
      {error ? <p className="mt-3 text-sm font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}

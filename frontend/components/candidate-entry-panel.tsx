"use client";

import { FileSearch, FileUp } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  extractCandidatesDocument,
  importCandidatesCsv,
  type CandidateImportResult,
  type Company,
  type ExtractedCandidateDraft
} from "@/lib/api";

export function CandidateEntryPanel({ companies }: { companies: Company[] }) {
  const router = useRouter();
  const [isProcessing, setIsProcessing] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<CandidateImportResult | null>(null);
  const [drafts, setDrafts] = useState<ExtractedCandidateDraft[]>([]);

  async function processFile(file: File, importCsv: boolean) {
    setError(null);
    setImportResult(null);
    setDrafts([]);
    if (importCsv && file.name.toLowerCase().endsWith(".csv")) {
      const result = await importCandidatesCsv(file);
      setImportResult(result);
      router.refresh();
      return;
    }
    const result = await extractCandidatesDocument(file);
    setDrafts(result.candidates);
  }

  async function onProcess(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || isProcessing) return;
    setIsProcessing(true);
    try {
      await processFile(file, true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setIsProcessing(false);
      event.target.value = "";
    }
  }

  async function onExtract(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || isExtracting) return;
    setIsExtracting(true);
    try {
      await processFile(file, false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "识别失败");
    } finally {
      setIsExtracting(false);
      event.target.value = "";
    }
  }

  return (
    <div id="candidate-upload" className="tn-surface rounded-lg p-5">
      <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <div>
          <div className="mb-3 flex items-center gap-2">
            <FileUp className="h-4 w-4 text-primary" />
            <h2 className="font-black">导入候选人文件</h2>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">
            只保留一个上传入口。CSV 会直接写入共享候选人数据库；PDF、Word、JSON、网页文本等会先智能识别候选人字段。
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <label className="tn-button tn-button-primary">
              <FileUp className="h-4 w-4" />
              {isProcessing ? "处理中" : "上传并处理"}
              <input type="file" onChange={onProcess} className="hidden" />
            </label>
            <label className="tn-button tn-button-secondary">
              <FileSearch className="h-4 w-4" />
              {isExtracting ? "识别中" : "仅智能识别"}
              <input type="file" onChange={onExtract} className="hidden" />
            </label>
          </div>
          {companies.length ? (
            <p className="mt-3 text-xs font-semibold text-muted-foreground">
              当前共享数据库包含 {companies.length} 个监测公司。
            </p>
          ) : null}
          {error ? <p className="mt-3 text-sm font-semibold text-red-700">{error}</p> : null}
        </div>

        <div>
          {importResult ? (
            <div className="rounded-md border bg-white p-4 text-sm leading-6">
              <p className="font-black">导入完成</p>
              <p>
                新增 {importResult.created_count} 条，重复 {importResult.duplicate_count} 条，失败{" "}
                {importResult.failed_count} 条。
              </p>
              {importResult.errors.map((item) => (
                <p key={item} className="text-red-700">
                  {item}
                </p>
              ))}
            </div>
          ) : drafts.length ? (
            <div className="grid max-h-72 gap-2 overflow-auto rounded-md border bg-white p-3">
              {drafts.slice(0, 10).map((draft, index) => (
                <div key={`${draft.name}-${index}`} className="rounded-md bg-muted/50 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-black">{draft.name ?? "未识别姓名"}</p>
                    <span className="rounded-md bg-white px-2 py-1 text-xs font-bold">
                      {Math.round(draft.confidence * 100)}%
                    </span>
                  </div>
                  <p className="mt-1 text-muted-foreground">
                    {draft.company_name ?? "未知公司"} / {draft.title ?? "未知岗位"} /{" "}
                    {draft.domain ?? "未知方向"}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-md border bg-white p-4 text-sm leading-6 text-muted-foreground">
              上传后的数据会和网页搜索确认入库的数据共用同一个数据库、评分和效能分析口径。
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

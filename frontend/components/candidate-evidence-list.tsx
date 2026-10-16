"use client";

import { ChevronDown, ExternalLink } from "lucide-react";
import { useState } from "react";

import { EvidenceConfirmButton } from "@/components/evidence-form";
import { evidenceDocumentUrl, type Evidence } from "@/lib/api";
import { SOURCE_LABELS } from "@/lib/labels";

export function CandidateEvidenceList({ evidence }: { evidence: Evidence[] }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <section className="tn-surface rounded-lg">
      <button
        type="button"
        onClick={() => setIsOpen((current) => !current)}
        className="tn-section-bar w-full text-left"
      >
        <div>
          <h2 className="font-black">信息列表</h2>
          <p className="mt-1 text-xs text-muted-foreground">手动上传和网页搜索确认保存的数据共享同一个数据库。</p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
          {evidence.length} 条
          <ChevronDown className={`h-4 w-4 transition ${isOpen ? "rotate-180" : ""}`} />
        </span>
      </button>

      {isOpen ? (
        <div className="divide-y divide-border">
          {evidence.map((item) => (
            <article key={item.id} className="px-5 py-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-black">{item.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {SOURCE_LABELS[item.source] ?? item.source} / {new Date(item.observed_at).toLocaleDateString("zh-CN")}
                  </p>
                </div>
                <span className="rounded-md bg-muted px-2 py-1 text-xs font-black">
                  {Math.round(item.confidence * 100)}%
                </span>
              </div>
              <p className="mt-3 text-sm leading-7 text-slate-700">{item.summary}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-md px-2 py-1 text-xs font-black ${
                    item.confirmed_by_user ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {item.confirmed_by_user ? "已保存确认" : "待确认"}
                </span>
                {item.url ? (
                  <a href={item.url} className="tn-link inline-flex items-center gap-2 text-sm" target="_blank" rel="noreferrer">
                    查看来源 <ExternalLink className="h-4 w-4" />
                  </a>
                ) : null}
                {item.screenshot_path?.startsWith("upload://") ? (
                  <a href={evidenceDocumentUrl(item.id)} className="tn-link inline-flex items-center gap-2 text-sm">
                    下载原文件 <ExternalLink className="h-4 w-4" />
                  </a>
                ) : null}
                {!item.confirmed_by_user ? <EvidenceConfirmButton evidenceId={item.id} /> : null}
              </div>
            </article>
          ))}
          {evidence.length === 0 ? <p className="px-5 py-4 text-sm text-muted-foreground">暂无已保存信息。</p> : null}
        </div>
      ) : null}
    </section>
  );
}

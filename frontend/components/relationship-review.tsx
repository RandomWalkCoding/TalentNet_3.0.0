"use client";
import Link from "next/link";
import { useState } from "react";
import { type Relationship, decideRelationship, rebuildRelationships } from "@/lib/api";

export function RelationshipReview({ initial }: { initial: Relationship[] }) {
  const [items, setItems] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function act(work: () => Promise<void>) {
    setBusy(true); setError("");
    try { await work(); } catch (e) { setError(e instanceof Error ? e.message : "操作失败"); }
    finally { setBusy(false); }
  }
  return <section className="tn-surface rounded-lg p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-black">关系线索审核</h2><button className="tn-button" disabled={busy} onClick={() => act(async () => setItems(await rebuildRelationships()))}>{busy ? "处理中…" : "生成 / 更新关系线索"}</button></div>
    <p className="mt-2 text-sm text-muted-foreground">依据已录入的同公司、同部门信息生成疑似关系，人工确认后才标记为已确认。每组最多处理 30 人。</p>
    {error && <p role="alert" className="mt-3 text-red-700">{error}</p>}
    {!items.length && <p className="mt-4 text-sm">暂无关系线索，点击生成开始审核。</p>}
    <div className="mt-4 grid gap-3">{items.map(item => <article key={item.id} className="rounded-md border p-4">
      <p className="font-bold"><Link href={`/candidates/${item.source_candidate_id}`}>{item.source_name}</Link> ↔ <Link href={`/candidates/${item.target_candidate_id}`}>{item.target_name}</Link> · 同部门</p>
      <p className="mt-2 text-sm">{item.explanation}</p>
      <p className="mt-2 text-xs text-muted-foreground">置信度 {Math.round(item.confidence * 100)}% · {item.evidence_ids.length} 条确认过的证据 · {({ confirmed: "已确认", rejected: "已否定", suspected: "待审核" } as Record<string,string>)[item.status]}</p>
      <div className="mt-2 flex flex-wrap gap-3">{item.evidence.map(evidence => <Link key={evidence.id} className="tn-link text-xs" href={`/candidates/${evidence.candidate_id}`}>{evidence.title}</Link>)}</div>
      <div className="mt-3 flex gap-2">{[ ["confirmed", "确认关系"], ["rejected", "否定关系"], ["suspected", "恢复待审核"] ].map(([status, label]) => <button key={status} className="tn-button" disabled={busy || item.status === status} onClick={() => act(async () => { const updated = await decideRelationship(item.id, status); setItems(current => current.map(row => row.id === updated.id ? updated : row)); })}>{label}</button>)}</div>
    </article>)}</div>
  </section>;
}

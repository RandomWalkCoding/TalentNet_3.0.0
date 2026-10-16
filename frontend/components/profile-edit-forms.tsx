"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { updateCandidate, updateCompany, type CandidateDetail, type Company } from "@/lib/api";

export function CandidateEditForm({ candidate, companies }: { candidate: CandidateDetail; companies: Company[] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await updateCandidate(candidate.id, {
        name: String(form.get("name")).trim(), title: String(form.get("title")).trim(),
        current_company_id: String(form.get("company")), department: String(form.get("department")).trim() || null,
        location: String(form.get("location")).trim() || null, domain: String(form.get("domain")).trim() || null,
        profile_summary: String(form.get("summary")).trim() || null
      });
      setMessage("资料已保存，评分已刷新。"); router.refresh();
    } catch (e) { setMessage(e instanceof Error ? e.message : "保存失败"); }
    finally { setBusy(false); }
  }
  return <details className="tn-surface rounded-lg p-5"><summary className="cursor-pointer font-black">编辑候选人资料</summary>
    <form onSubmit={save} className="mt-4 grid gap-3 md:grid-cols-2" key={candidate.updated_at}>
      <label className="text-sm">姓名<input className="tn-field mt-1" name="name" required maxLength={120} defaultValue={candidate.name} /></label>
      <label className="text-sm">岗位<input className="tn-field mt-1" name="title" required maxLength={160} defaultValue={candidate.title} /></label>
      <label className="text-sm">公司<select name="company" className="tn-field mt-1" defaultValue={candidate.current_company_id}>{companies.map(company => <option key={company.id} value={company.id}>{company.name}</option>)}</select></label>
      {[ ["department", "部门", candidate.department], ["location", "地区", candidate.location], ["domain", "方向", candidate.domain] ].map(([name, label, value]) => <label key={name} className="text-sm">{label}<input className="tn-field mt-1" name={name ?? ""} maxLength={120} defaultValue={value ?? ""} /></label>)}
      <label className="text-sm md:col-span-2">资料摘要<textarea name="summary" className="tn-field mt-1" rows={3} defaultValue={candidate.profile_summary ?? ""} /></label>
      <button disabled={busy} className="tn-button tn-button-primary">{busy ? "保存中…" : "保存资料"}</button><p className="self-center text-sm" role="status">{message}</p>
    </form>
  </details>;
}

export function CompanyEditForm({ company }: { company: Company }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await updateCompany(company.id, { name: String(form.get("name")).trim(), industry: String(form.get("industry")).trim(), website: String(form.get("website")).trim() || null, monitor_status: String(form.get("status")) });
      setMessage("公司已更新。"); router.refresh();
    } catch (e) { setMessage(e instanceof Error ? e.message : "保存失败"); }
    finally { setBusy(false); }
  }
  return <details className="border-t p-5"><summary className="cursor-pointer text-sm font-bold">编辑公司</summary><form onSubmit={save} className="mt-3 grid gap-3">
    <label className="text-sm">名称<input className="tn-field mt-1" name="name" required maxLength={120} defaultValue={company.name} /></label>
    <label className="text-sm">行业<input className="tn-field mt-1" name="industry" required maxLength={120} defaultValue={company.industry} /></label>
    <label className="text-sm">官网<input className="tn-field mt-1" name="website" type="url" maxLength={240} defaultValue={company.website ?? ""} /></label>
    <label className="text-sm">监测状态<select name="status" className="tn-field mt-1" defaultValue={company.monitor_status}><option value="active">监测中</option><option value="paused">暂停</option></select></label>
    <button disabled={busy} className="tn-button tn-button-secondary">{busy ? "保存中…" : "保存公司"}</button><p className="text-sm" role="status">{message}</p>
  </form></details>;
}

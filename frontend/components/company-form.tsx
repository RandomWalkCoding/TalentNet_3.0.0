"use client";

import { Building2, Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createCompany } from "@/lib/api";

export function CompanyForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [website, setWebsite] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await createCompany({
        name,
        industry,
        website: website || null
      });
      setName("");
      setIndustry("");
      setWebsite("");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "新建公司失败");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="tn-surface rounded-lg p-5" onSubmit={onSubmit}>
      <div className="mb-4 flex items-center gap-2">
        <Building2 className="h-4 w-4 text-primary" />
        <h2 className="font-black">新建公司</h2>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <input value={name} onChange={(event) => setName(event.target.value)} className="tn-field" placeholder="公司名称" required />
        <input value={industry} onChange={(event) => setIndustry(event.target.value)} className="tn-field" placeholder="行业" required />
        <input value={website} onChange={(event) => setWebsite(event.target.value)} className="tn-field" placeholder="官网，可选" />
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        {error ? <p className="text-sm font-semibold text-red-700">{error}</p> : <span />}
        <button type="submit" disabled={isSubmitting} className="tn-button tn-button-primary">
          <Plus className="h-4 w-4" />
          {isSubmitting ? "创建中" : "创建公司"}
        </button>
      </div>
    </form>
  );
}

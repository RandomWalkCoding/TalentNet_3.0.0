"use client";

import { Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { runTalentSourcing } from "@/lib/api";

export function CompanyWebSearchButton({
  companyId,
  companyName,
  industry
}: {
  companyId: string;
  companyName: string;
  industry?: string;
}) {
  const router = useRouter();
  const [isSearching, setIsSearching] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSearch() {
    if (isSearching) return;
    setIsSearching(true);
    setMessage(null);
    setError(null);
    try {
      const response = await runTalentSourcing({
        company_id: companyId,
        target_count: 12,
        public_site_scope: null,
        talent_profile: `${companyName} ${industry ?? ""} leadership engineer product research hiring public profile candidates`
      });
      setMessage(
        `已联网搜索 ${response.tasks.length} 条结果，${
          response.llm_used ? "搜索计划由真实 LLM 生成" : "使用本地兜底计划"
        }，确认后会进入共享候选人库。`
      );
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "联网搜索失败");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div className="grid gap-2">
      <button type="button" onClick={onSearch} disabled={isSearching} className="tn-button tn-button-secondary">
        <Sparkles className="h-4 w-4" />
        {isSearching ? "联网搜索中" : "联网搜索"}
      </button>
      {message ? <p className="text-xs font-semibold text-emerald-700">{message}</p> : null}
      {error ? <p className="text-xs font-semibold text-red-700">{error}</p> : null}
    </div>
  );
}

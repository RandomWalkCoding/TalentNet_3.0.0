import Link from "next/link";
import { Crosshair, FileUp } from "lucide-react";

import { CandidateEntryPanel } from "@/components/candidate-entry-panel";
import { EmptyState } from "@/components/empty-state";
import { QuickFeedbackControl } from "@/components/quick-feedback-control";
import { RiskBadge } from "@/components/risk-badge";
import { TalentPoolStatusControl } from "@/components/talent-pool-status-control";
import { getCompanies, getTalentPool } from "@/lib/api";
import { FOLLOW_STATUS_LABELS, PRIORITY_LABELS, RISK_LEVEL_LABELS } from "@/lib/labels";

type TalentPoolPageProps = {
  searchParams: Promise<{
    company_id?: string;
    risk_level?: string;
    status?: string;
    pending_feedback?: string;
  }>;
};

export default async function TalentPoolPage({ searchParams }: TalentPoolPageProps) {
  const params = await searchParams;
  const pendingFeedback = params.pending_feedback === "true";
  const [companies, items] = await Promise.all([
    getCompanies(),
    getTalentPool({
      company_id: params.company_id,
      risk_level: params.risk_level,
      status: params.status,
      pending_feedback: pendingFeedback
    })
  ]);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">Talent Pool</p>
        <h1 className="tn-title">人才猎场</h1>
        <p className="tn-copy">
          这里承接候选人列表和详情：看人、看风险、看证据状态、推进跟进和反馈。只有值得持续跟进的人才进入这里。
        </p>
      </div>

      <form className="tn-surface grid gap-3 rounded-lg p-4 md:grid-cols-4">
        <select name="company_id" defaultValue={params.company_id ?? ""} className="tn-field">
          <option value="">全部公司</option>
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
        <select name="risk_level" defaultValue={params.risk_level ?? ""} className="tn-field">
          <option value="">全部风险</option>
          {Object.entries(RISK_LEVEL_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select name="status" defaultValue={params.status ?? ""} className="tn-field">
          <option value="">全部状态</option>
          {Object.entries(FOLLOW_STATUS_LABELS)
            .filter(([value]) => ["watching", "contacted", "in_process", "closed"].includes(value))
            .map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
        </select>
        <div className="flex items-center justify-between gap-3">
          <label className="flex items-center gap-2 text-sm font-bold">
            <input
              type="checkbox"
              name="pending_feedback"
              value="true"
              defaultChecked={pendingFeedback}
              className="h-4 w-4"
            />
            待反馈
          </label>
          <button type="submit" className="tn-button tn-button-primary">
            筛选
          </button>
        </div>
      </form>

      <div className="grid gap-4">
        {items.length > 0 ? (
          items.map((item) => (
            <article key={item.id} className="tn-surface rounded-lg p-5">
              <div className="grid gap-4 xl:grid-cols-[1fr_auto]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Link href={`/candidates/${item.candidate_id}`} className="text-xl font-black hover:text-primary">
                      {item.candidate_name}
                    </Link>
                    <RiskBadge level={item.risk_level} />
                    <span className="rounded-md border bg-white px-2 py-1 text-xs font-black text-muted-foreground">
                      {PRIORITY_LABELS[item.priority] ?? item.priority}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {item.company_name} / {item.title} / {item.department ?? "未标注部门"} / {item.location ?? "未标注地点"}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    方向：{item.domain ?? "未标注"}。建议窗口：{item.recommended_window ?? "待补充证据后判断"}。
                  </p>
                </div>
                <div className="grid min-w-[18rem] gap-3 sm:grid-cols-3 xl:text-right">
                  <Metric label="风险" value={item.risk_score ?? "-"} danger />
                  <Metric label="置信度" value={item.confidence_score ?? "-"} />
                  <div>
                    <p className="text-xs font-bold text-muted-foreground">状态</p>
                    <div className="mt-2">
                      <TalentPoolStatusControl itemId={item.id} status={item.status} />
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
                <QuickFeedbackControl candidateId={item.candidate_id} />
                <Link href={`/candidates/${item.candidate_id}`} className="tn-button tn-button-secondary">
                  查看完整资料
                </Link>
              </div>
            </article>
          ))
        ) : (
          <div className="tn-surface rounded-lg p-4">
            <EmptyState
              icon={Crosshair}
              title="暂无猎场候选人"
              description="先去 AI 搜索候选人，把值得跟进的线索加入猎场。也可以在下方上传文件补充候选人。"
            />
          </div>
        )}
      </div>

      <div className="tn-surface rounded-lg p-5">
        <div className="mb-4 flex items-center gap-2">
          <FileUp className="h-4 w-4 text-primary" />
          <h2 className="font-black">导入候选人</h2>
        </div>
        <CandidateEntryPanel companies={companies} />
      </div>
    </section>
  );
}

function Metric({ label, value, danger = false }: { label: string; value: string | number; danger?: boolean }) {
  return (
    <div>
      <p className="text-xs font-bold text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-black ${danger ? "text-red-700" : ""}`}>{value}</p>
    </div>
  );
}

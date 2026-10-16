import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { CandidateDetailActions } from "@/components/candidate-detail-actions";
import { CandidateEvidenceList } from "@/components/candidate-evidence-list";
import { CandidateScoreCard } from "@/components/candidate-score-card";
import { RiskBadge } from "@/components/risk-badge";
import { getCandidate, getCompanies, getFeedback } from "@/lib/api";
import { AIInsightsPanel } from "@/components/ai-insights-panel";
import { FeedbackPanel } from "@/components/feedback-panel";
import { AddToPoolButton } from "@/components/add-to-pool-button";
import { EvidenceForm } from "@/components/evidence-form";
import { CandidateEditForm } from "@/components/profile-edit-forms";

type CandidatePageProps = {
  params: Promise<{
    id: string;
  }>;
};

export default async function CandidatePage({ params }: CandidatePageProps) {
  const { id } = await params;
  const [candidate, companies, feedback] = await Promise.all([getCandidate(id), getCompanies(), getFeedback(id)]);

  return (
    <section className="tn-page">
      <Link href="/candidates" className="tn-link inline-flex w-fit items-center gap-2 text-sm">
        <ArrowLeft className="h-4 w-4" /> 返回候选人列表
      </Link>

      <div className="tn-surface rounded-lg p-5">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="tn-kicker">候选人详情</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-black">{candidate.name}</h1>
              <RiskBadge level={candidate.latest_score?.risk_level ?? null} />
            </div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {candidate.company_name} / {candidate.department ?? "未标注部门"} / {candidate.title}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[28rem]">
            {[
              ["方向", candidate.domain ?? "-"],
              ["地区", candidate.location ?? "-"],
              ["证据", String(candidate.evidence.length)],
              ["状态", candidate.follow_status]
            ].map(([label, value]) => (
              <div key={label} className="rounded-md border bg-white p-3">
                <p className="text-xs font-bold text-muted-foreground">{label}</p>
                <p className="mt-2 truncate font-black">{value}</p>
              </div>
            ))}
          </div>
        </div>
        {candidate.profile_summary ? (
          <p className="mt-4 max-w-4xl text-sm leading-7 text-slate-700">{candidate.profile_summary}</p>
        ) : null}
        <CandidateDetailActions
          candidateId={candidate.id}
          companyId={candidate.current_company_id}
          candidateName={candidate.name}
          title={candidate.title}
          companyName={candidate.company_name}
        />
        <div className="mt-4"><AddToPoolButton candidateId={candidate.id} /></div>
      </div>

      <CandidateEditForm candidate={candidate} companies={companies} />
      <CandidateScoreCard candidateId={candidate.id} score={candidate.latest_score} />
      <CandidateEvidenceList evidence={candidate.evidence} />
      <EvidenceForm candidateId={candidate.id} companyId={candidate.current_company_id} />
      <AIInsightsPanel candidateId={candidate.id} />
      <FeedbackPanel candidateId={candidate.id} feedback={feedback} />
    </section>
  );
}

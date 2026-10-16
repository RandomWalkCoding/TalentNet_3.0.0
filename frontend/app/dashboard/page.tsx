import Link from "next/link";
import { ArrowRight, BarChart3, Crosshair, Search, ShieldAlert, UsersRound } from "lucide-react";

import { DashboardFoldoutSections } from "@/components/dashboard-foldout-sections";
import { getAnalyticsSummary, getCandidates, getCompanies, getManagerSummary, getTalentPool } from "@/lib/api";

export default async function DashboardPage() {
  const [companies, candidates, poolItems, analytics, manager] = await Promise.all([
    getCompanies(),
    getCandidates(),
    getTalentPool(),
    getAnalyticsSummary(),
    getManagerSummary()
  ]);
  const highRiskCandidates = candidates.filter((candidate) =>
    ["very_high", "high"].includes(candidate.risk_level ?? "")
  );
  const contacted = poolItems.filter((item) => ["contacted", "in_process", "closed"].includes(item.status));
  const topMetrics = [
    { label: "人才库", value: candidates.length, icon: UsersRound },
    { label: "高风险待判断", value: highRiskCandidates.length, icon: ShieldAlert },
    { label: "猎场跟进", value: poolItems.length, icon: Crosshair },
    { label: "已触达", value: contacted.length, icon: BarChart3 }
  ];

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">Overview</p>
        <h1 className="tn-title">情报总览</h1>
        <p className="tn-copy">
          总览只保留结果、瓶颈和折叠的辅助信息。日常动作从 AI 搜索开始，在人才猎场推进。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {topMetrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="tn-surface rounded-lg p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-bold text-muted-foreground">{metric.label}</p>
                <Icon className="h-4 w-4 text-primary" />
              </div>
              <p className="mt-3 text-3xl font-black">{metric.value}</p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="tn-surface rounded-lg">
          <div className="tn-section-bar">
            <div>
              <h2 className="font-black">当前漏斗</h2>
              <p className="mt-1 text-xs text-muted-foreground">从发现线索到进入流程的简化转化。</p>
            </div>
            <Link href="/browser-tasks" className="tn-button tn-button-primary">
              <Search className="h-4 w-4" />
              继续搜索
            </Link>
          </div>
          <div className="grid gap-3 p-5">
            {analytics.funnel.map((step) => (
              <div key={step.key} className="grid grid-cols-[8rem_1fr_auto] items-center gap-3 text-sm">
                <p className="font-bold text-muted-foreground">{step.label}</p>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{
                      width: `${Math.min(100, Math.max(6, (step.count / Math.max(candidates.length, 1)) * 100))}%`
                    }}
                  />
                </div>
                <p className="font-black">{step.count}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="tn-surface rounded-lg">
          <div className="tn-section-bar">
            <div>
              <h2 className="font-black">管理提醒</h2>
              <p className="mt-1 text-xs text-muted-foreground">合并管理者视图和效能分析，只保留可行动建议。</p>
            </div>
            <Link href="/talent-pool" className="tn-button tn-button-secondary">
              去猎场 <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-3 p-5">
            {manager.recommended_actions.map((action) => (
              <div key={action} className="rounded-md border bg-white p-3 text-sm font-semibold text-slate-700">
                {action}
              </div>
            ))}
          </div>
        </section>
      </div>

      <DashboardFoldoutSections companies={companies} />
    </section>
  );
}

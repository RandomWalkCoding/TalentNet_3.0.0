import { getAnalyticsSummary } from "@/lib/api";

export default async function AnalyticsPage() {
  const analytics = await getAnalyticsSummary();
  const maxFunnel = Math.max(...analytics.funnel.map((item) => item.count), 1);
  const maxTrend = Math.max(
    ...analytics.trend.flatMap((item) => [item.high_risk, item.in_pool, item.contacted]),
    1
  );

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">效能分析</p>
        <h1 className="tn-title">MVP 指标看板</h1>
        <p className="tn-copy">
          指标基于已保存的候选人、查看事件、AI 话术复制事件和跟进反馈计算。
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {analytics.metrics.map((metric) => (
          <div key={metric.key} className="tn-surface tn-metric rounded-lg p-5">
            <p className="text-sm font-bold text-muted-foreground">{metric.label}</p>
            <p className="mt-2 text-4xl font-black">{metric.display_value}</p>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{metric.description}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="tn-surface rounded-lg">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-black">反馈漏斗</h2>
            <p className="mt-1 text-xs text-muted-foreground">从风险识别到进入流程</p>
          </div>
          <div className="space-y-4 p-5">
            {analytics.funnel.map((step) => (
              <div key={step.key}>
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-bold">{step.label}</span>
                  <span className="font-black">{step.count}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.max((step.count / maxFunnel) * 100, step.count ? 8 : 0)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="tn-surface rounded-lg">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-black">简单趋势</h2>
            <p className="mt-1 text-xs text-muted-foreground">最近 14 个有数据的日期，按当日累计记录计算；删除历史记录会影响结果。</p>
          </div>
          <div className="grid gap-3 p-5">
            {analytics.trend.map((point) => (
              <div key={point.label} className="rounded-md border bg-white p-4">
                <p className="mb-3 text-sm font-black">{point.label}</p>
                {[
                  ["高风险", point.high_risk, "bg-red-600"],
                  ["已入猎场", point.in_pool, "bg-amber-600"],
                  ["已触达", point.contacted, "bg-primary"]
                ].map(([label, value, color]) => (
                  <div key={label} className="mb-3 last:mb-0">
                    <div className="mb-1 flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-bold">{label}</span>
                      <span className="font-black">{value}</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${color}`}
                        style={{
                          width: `${Math.max((Number(value) / maxTrend) * 100, Number(value) ? 8 : 0)}%`
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

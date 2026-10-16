import { ShieldCheck } from "lucide-react";

import { getManagerSummary } from "@/lib/api";
import { cookies } from "next/headers";
import { getDemoSession } from "@/lib/api";

export default async function ManagerPage() {
  const cookie = (await cookies()).toString();
  const session = await getDemoSession(cookie);
  if (session.role !== "admin") return <section className="tn-page"><h1 className="tn-title">没有访问权限</h1><p className="tn-copy">管理者视图仅管理员可访问。可在顶部切换演示用户来验证权限。</p></section>;
  const summary = await getManagerSummary(cookie);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">管理者视图</p>
        <h1 className="tn-title">团队挖猎效能与席位使用</h1>
        <p className="tn-copy">
          汇总猎场、触达、反馈和转化指标，帮助招聘负责人发现断点并推动 outcome 回流。
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {summary.metrics.map((metric) => (
          <div key={metric.key} className="tn-surface rounded-lg p-5">
            <p className="text-xs font-bold text-muted-foreground">{metric.label}</p>
            <p className="mt-2 text-3xl font-black">{metric.display_value}</p>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{metric.description}</p>
          </div>
        ))}
      </div>
      <div className="tn-surface rounded-lg p-5">
        <h2 className="font-black">席位使用 · {summary.seats.filter(seat => seat.active).length} 个启用席位</h2>
        <p className="tn-copy">已记录 {summary.audit_count} 次 API 操作、{summary.llm_run_count} 次摘要/话术生成。</p>
        <div className="overflow-x-auto"><table className="tn-table"><thead><tr><th>成员</th><th>角色</th><th>状态</th><th>API 操作</th><th>AI 生成</th></tr></thead><tbody>{summary.seats.map(seat => <tr key={seat.user_id}><td>{seat.name}</td><td>{seat.role === "admin" ? "管理员" : "成员"}</td><td>{seat.active ? "已启用" : "停用"}</td><td>{seat.activity_count}</td><td>{seat.llm_run_count}</td></tr>)}</tbody></table></div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="tn-surface overflow-hidden rounded-lg">
          <div className="border-b border-border px-5 py-4">
            <h2 className="font-black">团队反馈表</h2>
          </div>
          <table className="tn-table">
            <thead>
              <tr>
                <th>Owner</th>
                <th>猎场</th>
                <th>触达</th>
                <th>反馈</th>
                <th>成功</th>
                <th>反馈率</th>
                <th>转化率</th>
              </tr>
            </thead>
            <tbody>
              {summary.team_rows.map((row) => (
                <tr key={row.owner_user_id}>
                  <td className="font-black">{row.owner_user_id}</td>
                  <td>{row.pool_count}</td>
                  <td>{row.contacted_count}</td>
                  <td>{row.feedback_count}</td>
                  <td>{row.success_count}</td>
                  <td>{Math.round(row.feedback_rate * 100)}%</td>
                  <td>{Math.round(row.conversion_rate * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid gap-4">
          <div className="tn-surface rounded-lg p-5">
            <h2 className="font-black">风险分布</h2>
            <div className="mt-4 grid gap-2">
              {Object.entries(summary.risk_distribution).map(([level, count]) => (
                <div key={level} className="flex items-center justify-between rounded-md border bg-white px-3 py-2">
                  <span className="font-bold">{level}</span>
                  <span className="font-black">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="tn-surface rounded-lg p-5">
            <div className="mb-3 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-primary" />
              <h2 className="font-black">建议动作</h2>
            </div>
            <div className="grid gap-2">
              {summary.recommended_actions.map((item) => (
                <p key={item} className="rounded-md border bg-white p-3 text-sm leading-6">
                  {item}
                </p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

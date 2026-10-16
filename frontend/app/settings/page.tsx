import { getSourceConnections, getWorkspaceSettings } from "@/lib/api";
import { SourceConnectionsPanel } from "@/components/source-connections-panel";

export default async function SettingsPage() {
  const [settings, connections] = await Promise.all([getWorkspaceSettings(), getSourceConnections()]);
  return <section className="tn-page"><div className="tn-page-header"><p className="tn-kicker">工作区设置</p><h1 className="tn-title">本地 Demo 配置</h1><p className="tn-copy">{settings.notice}</p></div>
    <div className="tn-surface rounded-lg p-5"><h2 className="font-black">AI 与数据存储</h2><dl className="mt-4 grid gap-3 text-sm"><div>数据库：{settings.database}</div><div>LLM：{settings.llm.provider} / {settings.llm.model}</div><div>连接：{settings.llm.configured ? "已配置密钥" : "未配置 · 使用本地规则模板"}</div><div>兼容接口：{settings.llm.base_url}</div><div>降级模型：{settings.llm.fallback_model}</div></dl><p className="mt-4 text-xs text-muted-foreground">在项目 .env 配置 LLM 后重启后端。页面不返回密钥。</p></div>
    <SourceConnectionsPanel connections={connections} />
  </section>;
}

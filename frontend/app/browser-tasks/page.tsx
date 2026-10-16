import { AISearchResults } from "@/components/ai-search-results";
import { SourceConnectionsPanel } from "@/components/source-connections-panel";
import { getCompanies, getSourceConnections } from "@/lib/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function BrowserTasksPage() {
  const [companies, connections] = await Promise.all([getCompanies(), getSourceConnections()]);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">AI Sourcing</p>
        <h1 className="tn-title">AI 搜索候选人</h1>
        <p className="tn-copy">
          像指挥 AI 助手一样输入检索任务。系统会拆解搜索策略、读取公开网页结果，并把候选人线索结构化成可处理卡片。
        </p>
      </div>

      <AISearchResults companies={companies} />
      <SourceConnectionsPanel connections={connections} />
    </section>
  );
}

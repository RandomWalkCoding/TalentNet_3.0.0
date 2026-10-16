import { OrgGraphView } from "@/components/org-graph-view";
import { getCompanies, getOrgGraph } from "@/lib/api";
import { getRelationships } from "@/lib/api";
import { RelationshipReview } from "@/components/relationship-review";

export default async function OrgGraphPage() {
  const [graph, companies, relationships] = await Promise.all([getOrgGraph(), getCompanies(), getRelationships()]);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">组织视图</p>
        <h1 className="tn-title">公司、部门与候选人概览</h1>
        <p className="tn-copy">
          用简约的层级列表替代知识图谱，按公司归档部门和候选人，方便快速扫描、筛选和进入详情。
        </p>
      </div>

      <OrgGraphView graph={graph} companies={companies} />
      <RelationshipReview initial={relationships} />
    </section>
  );
}

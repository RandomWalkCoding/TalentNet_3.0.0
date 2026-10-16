import { CandidateEntryPanel } from "@/components/candidate-entry-panel";
import { CandidateLibraryTable } from "@/components/candidate-library-table";
import { getCandidates, getCompanies } from "@/lib/api";

export default async function CandidatesPage() {
  const [candidates, companies] = await Promise.all([getCandidates(), getCompanies()]);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">Talent Database</p>
        <h1 className="tn-title">人才库</h1>
        <p className="tn-copy">
          全量人才资产库。支持搜索、按公司/风险/状态筛选；猎场只放需要推进的人才。
        </p>
      </div>

      <CandidateEntryPanel companies={companies} />
      <CandidateLibraryTable candidates={candidates} companies={companies} />
    </section>
  );
}

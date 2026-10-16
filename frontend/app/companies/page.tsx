import { CompanyCandidateBrowser } from "@/components/company-candidate-browser";
import { CompanyForm } from "@/components/company-form";
import { getCandidates, getCompanies } from "@/lib/api";

export default async function CompaniesPage() {
  const [companies, candidates] = await Promise.all([getCompanies(), getCandidates()]);

  return (
    <section className="tn-page">
      <div className="tn-page-header">
        <p className="tn-kicker">竞对公司</p>
        <h1 className="tn-title">公司与候选人监测</h1>
        <p className="tn-copy">
          查看每家公司下的候选人、风险分布和共享数据状态。上传文件、网页搜索确认入库的数据都会进入同一个候选人库。
        </p>
      </div>

      <CompanyForm />
      <CompanyCandidateBrowser companies={companies} candidates={candidates} />
    </section>
  );
}

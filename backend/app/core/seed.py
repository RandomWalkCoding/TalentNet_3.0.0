from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Candidate, CandidateScore, Company, Evidence


def seed_demo_data(db: Session) -> None:
    if db.get(Company, "company_openai") is not None:
        return

    companies = [
        Company(
            id="company_openai",
            name="OpenAI",
            industry="AI Foundation Model",
            website="https://openai.com",
            monitor_status="active",
            last_scanned_at=datetime(2026, 6, 14, 8, 30, tzinfo=timezone.utc),
        ),
        Company(
            id="company_deepmind",
            name="Google DeepMind",
            industry="AI Research",
            website="https://deepmind.google",
            monitor_status="active",
            last_scanned_at=datetime(2026, 6, 14, 8, 20, tzinfo=timezone.utc),
        ),
        Company(
            id="company_bytedance",
            name="ByteDance Seed",
            industry="AI Application",
            website="https://www.bytedance.com",
            monitor_status="active",
            last_scanned_at=datetime(2026, 6, 14, 8, 10, tzinfo=timezone.utc),
        ),
    ]
    db.add_all(companies)

    candidates = [
        Candidate(
            id="cand_lin_chen",
            name="林晨",
            current_company_id="company_openai",
            title="Senior Research Engineer",
            department="Post-training Platform",
            location="San Francisco",
            domain="LLM Post-training",
            profile_summary="长期关注大模型后训练、评估和推理效率。Demo 种子数据用于展示高风险候选人链路。",
            source_type="imported",
            follow_status="new",
        ),
        Candidate(
            id="cand_maya_singh",
            name="Maya Singh",
            current_company_id="company_deepmind",
            title="Research Scientist",
            department="Agent Systems",
            location="London",
            domain="AI Agents",
            profile_summary="研究方向包括智能体规划、工具使用和长期记忆。",
            source_type="imported",
            follow_status="new",
        ),
        Candidate(
            id="cand_zhou_yu",
            name="周宇",
            current_company_id="company_bytedance",
            title="Tech Lead",
            department="AI Infra",
            location="Beijing",
            domain="Inference Infrastructure",
            profile_summary="负责推理平台和 GPU 资源调度，适合展示中风险观察样例。",
            source_type="manual",
            follow_status="new",
        ),
    ]
    db.add_all(candidates)

    evidence_items = [
        Evidence(
            id="ev_lin_profile",
            candidate_id="cand_lin_chen",
            company_id="company_openai",
            source="linkedin_visible",
            title="公开资料近期出现技能标签更新",
            url="https://example.com/demo/linkedin/lin-chen",
            observed_at=datetime(2026, 6, 14, 8, 45, tzinfo=timezone.utc),
            event_time=datetime(2026, 6, 12, tzinfo=timezone.utc),
            summary="Demo 可见页面摘要显示候选人近期新增了推理优化和评估平台相关技能标签。",
            raw_text="Demo sanitized page text.",
            confidence=0.76,
            confirmed_by_user=True,
        ),
        Evidence(
            id="ev_lin_research",
            candidate_id="cand_lin_chen",
            company_id="company_openai",
            source="arxiv",
            title="近 8 个月缺少公开论文更新",
            url="https://arxiv.org",
            observed_at=datetime(2026, 6, 14, 8, 50, tzinfo=timezone.utc),
            event_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
            summary="公开论文检索结果显示候选人近期科研产出节奏下降，需结合团队项目情况人工核实。",
            raw_text="Demo arXiv search summary.",
            confidence=0.68,
            confirmed_by_user=True,
        ),
        Evidence(
            id="ev_maya_agent",
            candidate_id="cand_maya_singh",
            company_id="company_deepmind",
            source="company_site",
            title="公开项目页显示仍在核心项目",
            url="https://example.com/demo/deepmind/maya",
            observed_at=datetime(2026, 6, 14, 8, 40, tzinfo=timezone.utc),
            event_time=datetime(2026, 5, 30, tzinfo=timezone.utc),
            summary="公司公开项目页仍将候选人列为 Agent Systems 核心成员，流动风险需谨慎判断。",
            raw_text="Demo company page summary.",
            confidence=0.82,
            confirmed_by_user=True,
        ),
        Evidence(
            id="ev_zhou_hiring",
            candidate_id="cand_zhou_yu",
            company_id="company_bytedance",
            source="job_site",
            title="同组推理岗位招聘数量下降",
            url="https://example.com/demo/jobs/bytedance-ai-infra",
            observed_at=datetime(2026, 6, 14, 8, 35, tzinfo=timezone.utc),
            event_time=datetime(2026, 6, 10, tzinfo=timezone.utc),
            summary="Demo 招聘页摘要显示同组推理基础设施岗位数量较前期减少，可能是团队节奏变化信号。",
            raw_text="Demo job page summary.",
            confidence=0.71,
            confirmed_by_user=True,
        ),
    ]
    db.add_all(evidence_items)

    scores = [
        CandidateScore(
            id="score_lin_seed",
            candidate_id="cand_lin_chen",
            risk_score=82,
            confidence_score=74,
            risk_level="high",
            recommended_window="未来 2 周内",
            reason_codes=["profile_activity", "research_silence"],
            explanation="公开资料更新与科研产出下降同时出现，建议加入优先观察名单。",
            limitations=["LinkedIn 信息来自 Demo 用户可见页面摘要，需人工确认。"],
            model_version="seed-v1",
        ),
        CandidateScore(
            id="score_maya_seed",
            candidate_id="cand_maya_singh",
            risk_score=38,
            confidence_score=78,
            risk_level="low",
            recommended_window="暂不建议主动触达",
            reason_codes=["market_signal"],
            explanation="公开项目页仍显示其在核心项目中，当前流动信号不足。",
            limitations=["仅基于 Demo 种子证据。"],
            model_version="seed-v1",
        ),
        CandidateScore(
            id="score_zhou_seed",
            candidate_id="cand_zhou_yu",
            risk_score=63,
            confidence_score=66,
            risk_level="medium",
            recommended_window="未来 1 个月观察",
            reason_codes=["team_signal"],
            explanation="同组招聘节奏变化值得观察，但缺少个人层面的强信号。",
            limitations=["招聘变化不能直接推断个人离职倾向。"],
            model_version="seed-v1",
        ),
    ]
    db.add_all(scores)
    db.commit()

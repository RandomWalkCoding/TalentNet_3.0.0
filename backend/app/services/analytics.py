from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateScore, Feedback, TalentPoolItem
from app.models.workspace import UsageEvent, LLMRun
from app.schemas.analytics import AnalyticsSummary, FunnelStep, MetricCard, TrendPoint


SUCCESS_OUTCOMES = {"in_process", "offer_sent", "hired"}
CONTACTED_OUTCOMES = {
    "contacted",
    "no_response",
    "rejected",
    "not_interested",
    "interested",
    "in_process",
    "offer_sent",
    "hired",
}
STRUCTURED_CHANNELS = {"linkedin", "maimai", "email"}


class AnalyticsService:
    def get_summary(self, db: Session) -> AnalyticsSummary:
        scores = list(db.scalars(select(CandidateScore)).all())
        pool_items = list(db.scalars(select(TalentPoolItem)).all())
        feedback_items = list(db.scalars(select(Feedback)).all())
        events = list(db.scalars(select(UsageEvent)).all())
        runs = list(db.scalars(select(LLMRun)).all())

        latest_scores = self._latest_scores(scores)
        scored_candidate_ids = set(latest_scores.keys())
        high_risk_candidate_ids = {
            candidate_id
            for candidate_id, score in latest_scores.items()
            if score.risk_level in {"very_high", "high"}
        }
        pool_candidate_ids = {item.candidate_id for item in pool_items}
        contacted_candidate_ids = {
            item.candidate_id for item in feedback_items if item.outcome in CONTACTED_OUTCOMES
        }
        feedback_candidate_ids = {item.candidate_id for item in feedback_items if item.outcome not in {"contacted", "bad_prediction"}}
        success_candidate_ids = {
            item.candidate_id for item in feedback_items if item.outcome in SUCCESS_OUTCOMES
        }
        structured_channel_candidate_ids = {
            item.candidate_id
            for item in feedback_items
            if item.contact_channel in STRUCTURED_CHANNELS
        }

        high_risk_rate = self._rate(len(high_risk_candidate_ids), len(scored_candidate_ids))
        pool_join_rate = self._rate(
            len(pool_candidate_ids & high_risk_candidate_ids), len(high_risk_candidate_ids)
        )
        contact_rate = self._rate(len(contacted_candidate_ids & pool_candidate_ids), len(pool_candidate_ids))
        feedback_rate = self._rate(
            len(feedback_candidate_ids & contacted_candidate_ids), len(contacted_candidate_ids)
        )
        success_rate = self._rate(len(success_candidate_ids), len(contacted_candidate_ids))
        channel_rate = self._rate(
            len(structured_channel_candidate_ids & contacted_candidate_ids),
            len(contacted_candidate_ids),
        )
        viewed_ids = {e.candidate_id for e in events if e.kind == "candidate_view"}
        copied_ids = {e.candidate_id for e in events if e.kind == "outreach_copy"}
        generated_ids = {r.candidate_id for r in runs if r.operation == "outreach"}

        metrics = [
            self._metric("high_risk_coverage_rate", "高风险占比", high_risk_rate, "高风险候选人 / 已评分候选人"),
            self._metric("high_risk_view_rate", "高风险查看率", self._rate(len(viewed_ids & high_risk_candidate_ids), len(high_risk_candidate_ids)), "已打开详情的高风险候选人 / 高风险候选人"),
            self._metric("pool_join_rate", "高风险入库率", pool_join_rate, "已加入猎场的高风险候选人 / 高风险候选人"),
            self._metric("contact_rate", "触达率", contact_rate, "已触达候选人 / 猎场候选人"),
            self._metric("feedback_rate", "反馈覆盖率", feedback_rate, "有反馈的已触达候选人 / 已触达候选人"),
            self._metric("success_rate", "流程转化率", success_rate, "进入流程或更后阶段候选人 / 已触达候选人"),
            self._metric("channel_record_rate", "触达渠道记录率", channel_rate, "有明确触达渠道的候选人 / 已触达候选人"),
            self._metric("outreach_adoption_rate", "AI 话术复制率", self._rate(len(copied_ids & generated_ids), len(generated_ids)), "已复制 AI 话术的候选人 / 已生成 AI 话术的候选人；复制不代表已发送"),
        ]
        funnel = [
            FunnelStep(key="high_risk", label="高风险", count=len(high_risk_candidate_ids)),
            FunnelStep(key="in_pool", label="已入库", count=len(pool_candidate_ids)),
            FunnelStep(key="contacted", label="已触达", count=len(contacted_candidate_ids)),
            FunnelStep(key="success", label="进入流程+", count=len(success_candidate_ids)),
        ]
        trend = self._trend(feedback_items, scores, pool_items)

        return AnalyticsSummary(metrics=metrics, funnel=funnel, trend=trend)

    def _latest_scores(self, scores: list[CandidateScore]) -> dict[str, CandidateScore]:
        latest: dict[str, CandidateScore] = {}
        for score in sorted(scores, key=lambda item: (item.created_at, item.id)):
            latest[score.candidate_id] = score
        return latest

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0
        return round(min(numerator / denominator, 1), 4)

    def _metric(self, key: str, label: str, value: float, description: str) -> MetricCard:
        return MetricCard(
            key=key,
            label=label,
            value=value,
            display_value=f"{value * 100:.0f}%",
            description=description,
        )

    def _trend(
        self, feedback_items: list[Feedback], scores: list[CandidateScore], pool_items: list[TalentPoolItem]
    ) -> list[TrendPoint]:
        days = sorted({item.created_at.date().isoformat() for item in feedback_items} | {item.added_at.date().isoformat() for item in pool_items} | {item.created_at.date().isoformat() for item in scores})[-14:]
        return [
            TrendPoint(
                label=label,
                high_risk=sum(score.risk_level in {"high", "very_high"} for score in self._latest_scores([s for s in scores if s.created_at.date().isoformat() <= label]).values()),
                in_pool=len({item.candidate_id for item in pool_items if item.added_at.date().isoformat() <= label}),
                contacted=len({item.candidate_id for item in feedback_items if item.created_at.date().isoformat() <= label and item.outcome in CONTACTED_OUTCOMES}),
            )
            for label in days
        ]

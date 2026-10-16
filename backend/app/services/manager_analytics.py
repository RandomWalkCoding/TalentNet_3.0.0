from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateScore, Feedback, TalentPoolItem
from app.models.workspace import DemoUser, AuditLog, LLMRun
from app.schemas.manager import ManagerMetric, ManagerSummary, ManagerTeamRow
from app.services.analytics import CONTACTED_OUTCOMES, SUCCESS_OUTCOMES


class ManagerAnalyticsService:
    def get_summary(self, db: Session) -> ManagerSummary:
        candidates = list(db.scalars(select(Candidate)).all())
        scores = list(db.scalars(select(CandidateScore)).all())
        pool_items = list(db.scalars(select(TalentPoolItem)).all())
        feedback_items = list(db.scalars(select(Feedback)).all())
        users = list(db.scalars(select(DemoUser)).all())
        audit = list(db.scalars(select(AuditLog)).all())
        llm_runs = list(db.scalars(select(LLMRun)).all())
        latest_scores = self._latest_scores(scores)
        risk_distribution = Counter(score.risk_level for score in latest_scores.values())
        owner_pool: dict[str, set[str]] = defaultdict(set)
        for item in pool_items:
            owner_pool[item.owner_user_id or "demo_manager"].add(item.candidate_id)
        feedback_by_owner: dict[str, list[Feedback]] = defaultdict(list)
        for owner, candidate_ids in owner_pool.items():
            feedback_by_owner[owner] = [
                item for item in feedback_items if item.candidate_id in candidate_ids
            ]

        team_rows = []
        for owner, candidate_ids in sorted(owner_pool.items()):
            owner_feedback = feedback_by_owner[owner]
            contacted = {
                item.candidate_id for item in owner_feedback if item.outcome in CONTACTED_OUTCOMES
            }
            success = {
                item.candidate_id for item in owner_feedback if item.outcome in SUCCESS_OUTCOMES
            }
            team_rows.append(
                ManagerTeamRow(
                    owner_user_id=owner,
                    pool_count=len(candidate_ids),
                    contacted_count=len(contacted),
                    feedback_count=len(owner_feedback),
                    success_count=len(success),
                    feedback_rate=self._rate(len({item.candidate_id for item in owner_feedback if item.outcome not in {"contacted", "bad_prediction"}} & contacted), len(contacted)),
                    conversion_rate=self._rate(len(success), max(len(contacted), 1)),
                )
            )
        metrics = [
            self._metric("candidate_count", "候选人数", len(candidates), "系统内候选人总数"),
            self._metric("pool_count", "猎场人数", len(pool_items), "已加入猎场的人才数"),
            self._metric("feedback_count", "反馈数", len(feedback_items), "团队已记录反馈数"),
            self._metric(
                "high_risk_count",
                "高风险候选人",
                risk_distribution.get("very_high", 0) + risk_distribution.get("high", 0),
                "极高和高风险候选人合计",
            ),
        ]
        actions = []
        if not pool_items:
            actions.append("先将高风险候选人加入人才猎场，形成团队行动队列。")
        if feedback_items and sum(row.feedback_rate for row in team_rows) / max(len(team_rows), 1) < 0.5:
            actions.append("反馈记录率偏低，建议每次触达后补录 outcome。")
        if risk_distribution.get("needs_review", 0):
            actions.append("存在待核实候选人，建议通过上传文档或网页任务补证据。")
        if not actions:
            actions.append("当前 MVP 管理指标健康，下一步可关注高风险候选人的转化效率。")
        return ManagerSummary(
            metrics=metrics,
            team_rows=team_rows,
            risk_distribution=dict(risk_distribution),
            recommended_actions=actions,
            audit_count=len(audit),
            llm_run_count=len(llm_runs),
            seats=[{"user_id": user.id, "name": user.name, "role": user.role, "active": user.active,
                    "activity_count": sum(row.user_id == user.id for row in audit),
                    "llm_run_count": sum(row.user_id == user.id for row in llm_runs)} for user in users],
        )

    def _latest_scores(self, scores: list[CandidateScore]) -> dict[str, CandidateScore]:
        latest: dict[str, CandidateScore] = {}
        for score in sorted(scores, key=lambda item: (item.created_at, item.id)):
            latest[score.candidate_id] = score
        return latest

    def _metric(self, key: str, label: str, value: float, description: str) -> ManagerMetric:
        display = str(int(value)) if float(value).is_integer() else f"{value:.1f}"
        return ManagerMetric(key=key, label=label, value=value, display_value=display, description=description)

    def _rate(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0
        return round(min(numerator / denominator, 1), 4)

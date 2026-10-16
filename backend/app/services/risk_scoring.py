from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Candidate, CandidateScore, Evidence

SOURCE_WEIGHTS = {
    "linkedin_visible": 1.05,
    "maimai_visible": 0.95,
    "manual": 0.9,
    "company_site": 1.15,
    "job_site": 0.95,
    "arxiv": 1.05,
    "patent": 1.05,
}

PROFILE_SOURCES = {"linkedin_visible", "maimai_visible", "manual"}
RESEARCH_SOURCES = {"arxiv", "patent"}
TEAM_SOURCES = {"job_site", "company_site"}


@dataclass(frozen=True)
class ScoreFeature:
    code: str
    weight: int
    confidence_weight: int
    summary: str
    evidence_ids: list[str]


class RiskScoringService:
    model_version = "rules-v2"

    def refresh_candidate_score(self, db: Session, candidate_id: str) -> CandidateScore:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )

        evidence_items = db.scalars(
            select(Evidence)
            .where(Evidence.candidate_id == candidate_id)
            .order_by(Evidence.observed_at.desc())
        ).all()
        score = self._calculate(candidate=candidate, evidence_items=list(evidence_items))
        db.add(score)
        db.commit()
        db.refresh(score)
        return score

    def get_latest_score(self, db: Session, candidate_id: str) -> CandidateScore:
        candidate = db.get(Candidate, candidate_id)
        if candidate is None:
            raise AppError(
                code="CANDIDATE_NOT_FOUND",
                message="Candidate does not exist.",
                status_code=404,
            )

        score = db.scalar(
            select(CandidateScore)
            .where(CandidateScore.candidate_id == candidate_id)
            .order_by(CandidateScore.created_at.desc(), CandidateScore.id.desc())
        )
        if score is None:
            return self.refresh_candidate_score(db, candidate_id)
        return score

    def _calculate(self, candidate: Candidate, evidence_items: list[Evidence]) -> CandidateScore:
        now = datetime.now(timezone.utc)
        features = self._extract_features(evidence_items)
        snapshot = self._input_snapshot(evidence_items, features, now)
        review_reasons = self._review_reasons(snapshot)

        if not evidence_items:
            return CandidateScore(
                id=f"score_{uuid4().hex}",
                candidate_id=candidate.id,
                risk_score=20,
                confidence_score=25,
                risk_level="needs_review",
                recommended_window="证据不足，需要先补充可确认信号",
                reason_codes=[],
                input_snapshot=snapshot,
                explanation=(
                    f"{candidate.name} 当前缺少可确认的证据，系统无法形成可靠的流动倾向判断。"
                ),
                limitations=["无证据时必须人工核实，不能输出确定性判断。"],
                model_version=self.model_version,
            )

        weighted_confidence = self._weighted_confidence(evidence_items, now)
        source_bonus = min(int(snapshot["source_weight_total"] * 3), 18)
        evidence_bonus = min(snapshot["confirmed_count"] * 5 + snapshot["unconfirmed_count"] * 2, 18)
        freshness_bonus = min(snapshot["fresh_count"] * 4, 14)
        base_score = 22 + sum(feature.weight for feature in features)
        risk_score = max(0, min(100, base_score + source_bonus + evidence_bonus + freshness_bonus))

        confidence_score = int(
            max(
                0,
                min(
                    100,
                    weighted_confidence * 65
                    + min(snapshot["confirmed_count"], 4) * 7
                    + sum(feature.confidence_weight for feature in features)
                    - snapshot["unconfirmed_count"] * 8
                    - snapshot["stale_count"] * 5,
                ),
            )
        )

        risk_level = self._risk_level(risk_score=risk_score, confidence_score=confidence_score)
        recommended_window = self._recommended_window(risk_level)
        reason_codes = [feature.code for feature in features]
        explanation = self._explanation(candidate, features, risk_level, review_reasons)
        limitations = [
            "评分仅用于排序和提示，不代表确定离职判断。",
            "所有低置信度或未确认来源都需要人工核实后再用于触达决策。",
        ]
        if review_reasons:
            limitations.extend(review_reasons)

        return CandidateScore(
            id=f"score_{uuid4().hex}",
            candidate_id=candidate.id,
            risk_score=risk_score,
            confidence_score=confidence_score,
            risk_level=risk_level,
            recommended_window=recommended_window,
            reason_codes=reason_codes,
            input_snapshot=snapshot,
            explanation=explanation,
            limitations=limitations,
            model_version=self.model_version,
        )

    def _extract_features(self, evidence_items: list[Evidence]) -> list[ScoreFeature]:
        sources = {item.source for item in evidence_items}
        text = " ".join([item.title + " " + item.summary for item in evidence_items]).lower()
        features: list[ScoreFeature] = []

        if sources & PROFILE_SOURCES or any("profile" in item.title.lower() for item in evidence_items):
            features.append(
                ScoreFeature(
                    code="profile_activity",
                    weight=20,
                    confidence_weight=5,
                    summary="公开履历或资料出现活跃变化",
                    evidence_ids=[item.id for item in evidence_items if item.source in PROFILE_SOURCES],
                )
            )
        if sources & RESEARCH_SOURCES or any(term in text for term in ["paper", "research", "论文", "专利"]):
            features.append(
                ScoreFeature(
                    code="research_silence",
                    weight=14,
                    confidence_weight=4,
                    summary="公开科研或专利产出节奏变化",
                    evidence_ids=[item.id for item in evidence_items if item.source in RESEARCH_SOURCES],
                )
            )
        if sources & TEAM_SOURCES or any(term in text for term in ["hiring", "team", "招聘", "团队"]):
            features.append(
                ScoreFeature(
                    code="team_signal",
                    weight=13,
                    confidence_weight=3,
                    summary="团队、岗位或组织信号出现变化",
                    evidence_ids=[item.id for item in evidence_items if item.source in TEAM_SOURCES],
                )
            )
        if any(term in text for term in ["anniversary", "vesting", "入职周年", "期权"]):
            features.append(
                ScoreFeature(
                    code="career_anniversary",
                    weight=11,
                    confidence_weight=2,
                    summary="职业周期或潜在期权窗口接近",
                    evidence_ids=[item.id for item in evidence_items],
                )
            )
        if any(term in text for term in ["peer", "coworker", "同事", "合作者"]):
            features.append(
                ScoreFeature(
                    code="peer_movement",
                    weight=11,
                    confidence_weight=2,
                    summary="同事或合作者出现流动信号",
                    evidence_ids=[item.id for item in evidence_items],
                )
            )
        return features

    def _input_snapshot(
        self, evidence_items: list[Evidence], features: list[ScoreFeature], now: datetime
    ) -> dict:
        evidence_snapshots = []
        for item in evidence_items:
            age_days = self._age_days(item.observed_at, now)
            source_weight = SOURCE_WEIGHTS.get(item.source, 0.85)
            evidence_snapshots.append(
                {
                    "id": item.id,
                    "source": item.source,
                    "source_weight": source_weight,
                    "confidence": item.confidence,
                    "confirmed_by_user": item.confirmed_by_user,
                    "age_days": age_days,
                    "is_fresh": age_days <= 45,
                    "title": item.title,
                }
            )
        return {
            "evidence_count": len(evidence_items),
            "confirmed_count": sum(1 for item in evidence_items if item.confirmed_by_user),
            "unconfirmed_count": sum(1 for item in evidence_items if not item.confirmed_by_user),
            "fresh_count": sum(1 for item in evidence_snapshots if item["is_fresh"]),
            "stale_count": sum(1 for item in evidence_snapshots if not item["is_fresh"]),
            "avg_confidence": round(
                sum(item.confidence for item in evidence_items) / len(evidence_items), 3
            )
            if evidence_items
            else 0,
            "source_weight_total": round(
                sum(item["source_weight"] for item in evidence_snapshots), 3
            ),
            "features": [
                {
                    "code": feature.code,
                    "weight": feature.weight,
                    "confidence_weight": feature.confidence_weight,
                    "summary": feature.summary,
                    "evidence_ids": feature.evidence_ids,
                }
                for feature in features
            ],
            "evidence": evidence_snapshots,
        }

    def _weighted_confidence(self, evidence_items: list[Evidence], now: datetime) -> float:
        if not evidence_items:
            return 0
        total_weight = 0.0
        weighted = 0.0
        for item in evidence_items:
            source_weight = SOURCE_WEIGHTS.get(item.source, 0.85)
            confirmation_weight = 1.0 if item.confirmed_by_user else 0.55
            freshness_weight = 1.0 if self._age_days(item.observed_at, now) <= 45 else 0.7
            weight = source_weight * confirmation_weight * freshness_weight
            weighted += item.confidence * weight
            total_weight += weight
        return weighted / total_weight if total_weight else 0

    def _review_reasons(self, snapshot: dict) -> list[str]:
        reasons: list[str] = []
        if snapshot["evidence_count"] < 2:
            reasons.append("证据数量不足，建议至少补充两条不同来源信号。")
        if snapshot["unconfirmed_count"] > 0:
            reasons.append("存在未确认入库证据，需要用户确认来源可靠性。")
        if snapshot["avg_confidence"] < 0.65:
            reasons.append("证据平均置信度偏低，需要人工复核。")
        if snapshot["stale_count"] > 0:
            reasons.append("存在过期证据，需要补充近期信号。")
        return reasons

    def _age_days(self, value: datetime, now: datetime) -> int:
        observed_at = value
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        return max((now - observed_at).days, 0)

    def _risk_level(self, risk_score: int, confidence_score: int) -> str:
        if confidence_score < 60:
            return "needs_review"
        if risk_score >= 85:
            return "very_high"
        if risk_score >= 70:
            return "high"
        if risk_score >= 40:
            return "medium"
        return "low"

    def _recommended_window(self, risk_level: str) -> str:
        return {
            "very_high": "未来 1 周内优先触达",
            "high": "未来 2 周内",
            "medium": "未来 1 个月观察",
            "low": "暂不建议主动触达",
            "needs_review": "证据不足或置信度偏低，需要人工核实",
        }[risk_level]

    def _explanation(
        self,
        candidate: Candidate,
        features: list[ScoreFeature],
        risk_level: str,
        review_reasons: list[str],
    ) -> str:
        if not features:
            return f"{candidate.name} 当前证据较少，系统将其标记为待核实。"
        feature_text = "；".join(feature.summary for feature in features)
        review_text = f" 待核实原因：{'；'.join(review_reasons)}" if review_reasons else ""
        return (
            f"{candidate.name} 的当前判断依据包括：{feature_text}。"
            f"系统按规则模型计算后标记为 {risk_level}。{review_text}"
        )

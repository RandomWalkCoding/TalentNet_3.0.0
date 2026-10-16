from pydantic import BaseModel


class ManagerMetric(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    description: str


class ManagerTeamRow(BaseModel):
    owner_user_id: str
    pool_count: int
    contacted_count: int
    feedback_count: int
    success_count: int
    feedback_rate: float
    conversion_rate: float


class ManagerSummary(BaseModel):
    metrics: list[ManagerMetric]
    team_rows: list[ManagerTeamRow]
    risk_distribution: dict[str, int]
    recommended_actions: list[str]
    seats: list[dict] = []
    audit_count: int = 0
    llm_run_count: int = 0

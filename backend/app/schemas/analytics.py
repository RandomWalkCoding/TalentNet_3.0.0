from pydantic import BaseModel


class MetricCard(BaseModel):
    key: str
    label: str
    value: float
    display_value: str
    description: str


class FunnelStep(BaseModel):
    key: str
    label: str
    count: int


class TrendPoint(BaseModel):
    label: str
    high_risk: int
    in_pool: int
    contacted: int


class AnalyticsSummary(BaseModel):
    metrics: list[MetricCard]
    funnel: list[FunnelStep]
    trend: list[TrendPoint]

from pydantic import BaseModel


class OrgGraphNode(BaseModel):
    id: str
    label: str
    type: str
    status: str
    meta: dict = {}


class OrgGraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    confidence: float


class OrgGraphResponse(BaseModel):
    company_id: str | None = None
    nodes: list[OrgGraphNode]
    edges: list[OrgGraphEdge]

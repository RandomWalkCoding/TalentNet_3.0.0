from pydantic import BaseModel


class SourceConnectionRead(BaseModel):
    provider: str
    label: str
    status: str
    mode: str
    requires_user_login: bool
    notes: str


class SourceConnectionUpdate(BaseModel):
    status: str

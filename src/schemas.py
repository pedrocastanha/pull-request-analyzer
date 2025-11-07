from typing import Optional
from pydantic import BaseModel


class AnalyzePRResponse(BaseModel):
    status: str
    message: str
    pr_id: int
    analysis: Optional[dict] = None
    error: Optional[str] = None


class AnalyzePRRequest(BaseModel):
    pull_request_id: int

from pydantic import BaseModel


class AnalyzePRResponse(BaseModel):
    status: str
    message: str
    pr_id: int
    analysis: dict = None
    error: str = None

class AnalyzePRRequest(BaseModel):
    pull_request_id: int
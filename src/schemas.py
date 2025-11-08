from typing import Optional, List, Any, Dict
from pydantic import BaseModel


class AnalyzePRResponse(BaseModel):
    status: str
    message: str
    pr_id: int
    comments: List[Dict[str, Any]] = []
    total_comments: int = 0
    error: Optional[str] = None


class AnalyzePRRequest(BaseModel):
    pull_request_id: int

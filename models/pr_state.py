from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class FileChange(BaseModel):
    filename: str
    status: str
    additions: int
    deletions: int
    patch: Optional[str] = None
    before_content: Optional[str] = None
    after_content: Optional[str] = None

class SecurityIssue(BaseModel):
    severity:str
    description: str
    file:str
    line: Optional[int] = None
    suggestion: Optional[str] = None

class CodeQualityIssue(BaseModel):
    type: str
    description: str
    file: str
    line: Optional[int] = None
    suggestion: str

class AnalysisResult(BaseModel):
    category: str
    score: float
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    summary: str = ""

class PRState(BaseModel):
    """Estado da análise do PR"""
    repo_owner: str
    repo_name: str
    pr_number: int
    pr_title: str = ""
    pr_description: str = ""
    pr_author: str = ""
    base_branch: str = "main"
    head_branch: str = ""

    status: AnalysisStatus = AnalysisStatus.PENDING
    current_step: str = "init"
    progress: float = 0.0

    files_changed: List[FileChange] = Field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0

    analysis_results: Dict[str, AnalysisResult] = Field(default_factory=dict)
    security_issues: List[SecurityIssue] = Field(default_factory=list)
    quality_issues: List[CodeQualityIssue] = Field(default_factory=list)

    overall_score: float = 0.0
    complexity_score: float = 0.0
    test_coverage_estimated: float = 0.0

    execution_log: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.execution_log.append(f"[{timestamp}] {message}")
        self.updated_at = datetime.now()

    def update_progress(self, step: str, progress: float):
        self.current_step = step
        self.progress = min(100.0, max(0.0, progress))
        self.log(f"Progresso: {progress:.1f}% - {step}")

    def add_error(self, error: str):
        self.errors.append(error)
        self.log(f"ERRO: {error}")

    def get_summary(self) -> Dict[str, Any]:
        return {
            "pr_info": {
                "repository": f"{self.repo_owner}/{self.repo_name}",
                "number": self.pr_number,
                "title": self.pr_title,
                "author": self.pr_author
            },
            "changes": {
                "files_changed": len(self.files_changed),
                "additions": self.total_additions,
                "deletions": self.total_deletions
            },
            "analysis": {
                "status": self.status,
                "progress": self.progress,
                "overall_score": self.overall_score,
                "security_issues": len(self.security_issues),
                "quality_issues": len(self.quality_issues)
            },
            "categories_analyzed": list(self.analysis_results.keys())
        }

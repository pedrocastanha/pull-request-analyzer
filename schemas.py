from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

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
    severity: str
    description: str
    file: str
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

# Novos schemas para o fluxo de três agentes
class Module(BaseModel):
    id: str
    name: str
    files: List[str]
    reason: str
    type: str  # independent|interactive|feature

class SeparatorResult(BaseModel):
    modules: List[Module]
    summary: str

class CategoryAnalysis(BaseModel):
    score: float
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class ModuleAnalysis(BaseModel):
    overall_score: float
    categories: Dict[str, CategoryAnalysis]

class Recommendation(BaseModel):
    priority: str  # high|medium|low
    category: str  # security|quality|performance|architecture|tests
    description: str
    suggestion: str
    files: List[str]
    lines: Optional[List[int]] = None

class ResearchSource(BaseModel):
    source: str  # documentation|google
    query: str
    findings: str

class AnalyzerResult(BaseModel):
    module_id: str
    analysis: ModuleAnalysis
    recommendations: List[Recommendation]
    research_sources: List[ResearchSource]

class ImprovementPlan(BaseModel):
    immediate_actions: List[str]
    short_term: List[str]
    long_term: List[str]

class CodeExample(BaseModel):
    current: str
    improved: str
    explanation: str

class ModuleAnalysisCommentary(BaseModel):
    module_name: str
    overall_health: str  # excellent|good|needs_improvement|critical
    key_issues: List[str]
    improvement_plan: ImprovementPlan
    code_examples: Optional[CodeExample] = None

class ActionableRecommendation(BaseModel):
    priority: str  # critical|high|medium|low
    title: str
    description: str
    steps: List[str]
    expected_benefit: str
    estimated_effort: str  # low|medium|high

class LearningResource(BaseModel):
    topic: str
    resources: List[str]
    why_important: str

class CommentatorResult(BaseModel):
    executive_summary: str
    modules_analysis: List[ModuleAnalysisCommentary]
    actionable_recommendations: List[ActionableRecommendation]
    learning_resources: List[LearningResource]
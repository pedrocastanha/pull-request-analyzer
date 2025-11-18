from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class IssueBase(BaseModel):
    file: str = Field(description="File path where the issue was found")
    line: int = Field(description="Line number where the issue starts")
    final_line: Optional[int] = Field(None, description="Final line number if issue spans multiple lines")
    type: Optional[str] = Field(None, description="Type/category of the issue")
    description: Optional[str] = Field(None, description="Detailed description of the issue")
    evidence: Optional[str] = Field(None, description="Code snippet showing the problematic code")
    impact: Optional[str] = Field(None, description="Impact and consequences of this issue")
    recommendation: Optional[str] = Field(None, description="How to fix this issue")
    example: Optional[str] = Field(None, description="Example of corrected code")
    category: Optional[str] = Field(None, description="PROBLEM or SUGGESTION")
    severity: Optional[str] = Field(None, description="Issue severity level")
    title: Optional[str] = Field(None, description="Short title of the issue")


class SecurityAnalysis(BaseModel):
    issues: List[IssueBase] = Field(default_factory=list, description="List of security issues found")
    summary: Optional[str] = Field(None, description="Summary of security analysis")


class PerformanceAnalysis(BaseModel):
    issues: List[IssueBase] = Field(default_factory=list, description="List of performance issues found")
    summary: Optional[str] = Field(None, description="Summary of performance analysis")


class CleanCodeAnalysis(BaseModel):
    issues: List[IssueBase] = Field(default_factory=list, description="List of code quality issues found")
    summary: Optional[str] = Field(None, description="Summary of clean code analysis")


class LogicalAnalysis(BaseModel):
    issues: List[IssueBase] = Field(default_factory=list, description="List of logical bugs found")
    summary: Optional[str] = Field(None, description="Summary of logical analysis")


class ReviewerComment(BaseModel):
    file: str = Field(description="File path")
    line: int = Field(description="Line number")
    final_line: Optional[int] = Field(None, description="Final line if spans multiple lines")
    message: str = Field(description="Complete formatted message for Azure DevOps")


class ReviewerAnalysis(BaseModel):
    comments: List[ReviewerComment] = Field(default_factory=list, description="List of consolidated comments for PR")


class AnalyzePRRequest(BaseModel):
    pull_request_id: int


class AnalyzePRResponse(BaseModel):
    status: str
    message: str
    pr_id: int
    comments: List[Dict[str, Any]] = []
    total_comments: int = 0
    error: Optional[str] = None

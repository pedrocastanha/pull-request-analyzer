import operator
from typing import TypedDict, Optional, Dict, List, Any, Annotated


class PRAnalysisState(TypedDict):
    pr_id: int
    project_type: str
    repository_id: str
    pr_data: Optional[Dict[str, Any]]
    error: Annotated[list, operator.add]
    security_analysis: Optional[Dict[str, Any]]
    performance_analysis: Optional[Dict[str, Any]]
    clean_code_analysis: Optional[Dict[str, Any]]
    logical_analysis: Optional[Dict[str, Any]]
    api_design_analyst_output: Optional[Dict[str, Any]]
    error_handling_analyst_output: Optional[Dict[str, Any]]
    reviewer_analysis: Optional[Dict[str, Any]]
    published_comments: Optional[List[Dict[str, Any]]]
    next_node: Optional[str]
    _rag_manager: Optional[Any]
    batches: Optional[List[List[Dict[str, Any]]]]
    current_batch_index: int
    total_batches: int
    batch_analyses: Annotated[list, operator.add]


def create_initial_state(
    pr_id: int, project_type: str = "java", repository_id: str = None
) -> PRAnalysisState:
    return {
        "pr_id": pr_id,
        "project_type": project_type,
        "repository_id": repository_id,
        "pr_data": None,
        "error": [],
        "security_analysis": None,
        "performance_analysis": None,
        "clean_code_analysis": None,
        "logical_analysis": None,
        "api_design_analyst_output": None,
        "error_handling_analyst_output": None,
        "reviewer_analysis": None,
        "published_comments": None,
        "next_node": None,
        "_rag_manager": None,
        "batches": None,
        "current_batch_index": 0,
        "total_batches": 0,
        "batch_analyses": [],
    }


def has_error(state: PRAnalysisState) -> bool:
    return len(state.get("error", [])) > 0


def has_pr_data(state: PRAnalysisState) -> bool:
    return state.get("pr_data") is not None

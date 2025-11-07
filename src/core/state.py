from typing import TypedDict, Optional, Dict, List, Any


class PRAnalysisState(TypedDict):
    pr_id: int
    pr_data: Optional[Dict[str, Any]]
    error: Optional[str]
    security_analysis: Optional[Dict[str, Any]]
    performance_analysis: Optional[Dict[str, Any]]
    clean_code_analysis: Optional[Dict[str, Any]]
    logical_analysis: Optional[Dict[str, Any]]
    reviewer_analysis: Optional[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]

def create_initial_state(pr_id: int) -> PRAnalysisState:
    return {
        "pr_id": pr_id,
        "pr_data": None,
        "error": None,
        "security_analysis": None,
        "performance_analysis": None,
        "clean_code_analysis": None,
        "logical_analysis": None,
        "reviewer_analysis": None,
        "final_report": None,
    }


def has_error(state: PRAnalysisState) -> bool:
    return state.get("error") is not None


def has_pr_data(state: PRAnalysisState) -> bool:
    return state.get("pr_data") is not None
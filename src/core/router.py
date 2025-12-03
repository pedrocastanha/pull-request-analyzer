import logging
from typing import Literal

from src.core import PRAnalysisState

logger = logging.getLogger(__name__)


def should_continue_or_end(state: PRAnalysisState) -> Literal["reviewer_agent", "END"]:
    if state.get("error"):
        logger.error(
            f"[ROUTER: should_continue_or_end] Error detected, ending workflow"
        )
        return "END"
    logger.info(f"[ROUTER: should_continue_or_end] No errors, proceeding to analyses")
    return "reviewer_agent"


def route_reviewer_decision(state: PRAnalysisState) -> str:
    next_node = state.get("next_node", "END")
    logger.info(f"[ROUTER: route_reviewer_decision] Reviewer decision: {next_node}")
    return next_node


def should_review_batch_or_skip(
    state: PRAnalysisState,
) -> Literal["reviewer_agent", "check_next_batch"]:
    security = state.get("security_analysis")
    performance = state.get("performance_analysis")
    clean_code = state.get("clean_code_analysis")
    logical = state.get("logical_analysis")
    api_design = state.get("api_design_analyst_output")
    error_handling = state.get("error_handling_analyst_output")

    analyses_status = {
        "security": security is not None,
        "performance": performance is not None,
        "clean_code": clean_code is not None,
        "logical": logical is not None,
        "api_design": api_design is not None,
        "error_handling": error_handling is not None,
    }

    completed_count = sum(analyses_status.values())

    if completed_count > 0:
        logger.info(
            f"[ROUTER: should_review_batch] Batch has {completed_count} completed analyses, "
            f"proceeding to reviewer"
        )
        return "reviewer_agent"
    else:
        logger.info(
            f"[ROUTER: should_review_batch] Batch failed completely, skipping reviewer"
        )
        return "check_next_batch"


def should_process_next_batch_or_end(
    state: PRAnalysisState,
) -> Literal["setup_rag", "cleanup"]:
    current = state.get("current_batch_index", 0)
    total = state.get("total_batches", 0)

    if current < total:
        logger.info(
            f"[ROUTER: should_process_next_batch] Processing next batch: "
            f"{current + 1}/{total}"
        )
        return "setup_rag"
    else:
        logger.info(
            f"[ROUTER: should_process_next_batch] All batches processed ({total}/{total}), "
            f"proceeding to cleanup"
        )
        return "cleanup"

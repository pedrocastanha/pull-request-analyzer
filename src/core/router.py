import logging
from typing import Literal

from src.core import PRAnalysisState

logger = logging.getLogger(__name__)

def should_continue_or_end(state: PRAnalysisState) -> Literal["reviewer_agent", "END"]:
    if state.get("error"):
        logger.error(f"[ROUTER: should_continue_or_end] Error detected, ending workflow")
        return "END"
    logger.info(f"[ROUTER: should_continue_or_end] No errors, proceeding to analyses")
    return "reviewer_agent"

def route_reviewer_decision(state: PRAnalysisState) -> str:
    next_node = state.get("next_node", "END")
    logger.info(f"[ROUTER: route_reviewer_decision] Reviewer decision: {next_node}")
    return next_node
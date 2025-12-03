import logging
from typing import Dict, Any

from src.core import PRAnalysisState

logger = logging.getLogger(__name__)


async def aggregate_analyses_node(state: PRAnalysisState) -> Dict[str, Any]:
    current_batch_index = state.get("current_batch_index", 0)
    total_batches = state.get("total_batches", 0)

    logger.info(
        f"[NODE: aggregate_analyses] Checking batch {current_batch_index + 1}/{total_batches} - "
        f"all parallel analyses completed?"
    )

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
    total_count = len(analyses_status)

    logger.info(
        f"[NODE: aggregate_analyses] Completed: {completed_count}/{total_count}"
    )
    for agent_name, is_completed in analyses_status.items():
        status_emoji = "✓" if is_completed else "✗"
        logger.info(f"  {status_emoji} {agent_name}: {is_completed}")

    if completed_count == total_count:
        logger.info(
            f"[NODE: aggregate_analyses] ✓ Batch {current_batch_index + 1} completed successfully"
        )
    elif completed_count > 0:
        logger.warning(
            f"[NODE: aggregate_analyses] Batch {current_batch_index + 1} partially completed "
            f"({completed_count}/{total_count})"
        )
    else:
        logger.error(
            f"[NODE: aggregate_analyses] Batch {current_batch_index + 1} completely failed"
        )

    return {"current_batch_index": current_batch_index + 1}

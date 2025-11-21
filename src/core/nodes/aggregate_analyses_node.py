import logging
from typing import Dict, Any

from src.core import PRAnalysisState

logger = logging.getLogger(__name__)


async def aggregate_analyses_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: aggregate_analyses] Checking if all parallel analyses completed")

    security = state.get("security_analysis")
    performance = state.get("performance_analysis")
    clean_code = state.get("clean_code_analysis")
    logical = state.get("logical_analysis")

    analyses_status = {
        "security": security is not None,
        "performance": performance is not None,
        "clean_code": clean_code is not None,
        "logical": logical is not None
    }

    completed_count = sum(analyses_status.values())
    total_count = len(analyses_status)

    logger.info(f"[NODE: aggregate_analyses] Completed: {completed_count}/{total_count}")
    for agent_name, is_completed in analyses_status.items():
        status_emoji = "✅" if is_completed else "❌"
        logger.info(f"  {status_emoji} {agent_name}: {is_completed}")

    if completed_count < total_count:
        error_msg = f"Not all analyses completed. Status: {analyses_status}"
        logger.error(f"[NODE: aggregate_analyses] {error_msg}")
        return {"error": error_msg}

    logger.info("[NODE: aggregate_analyses] ✓ All parallel analyses completed successfully")

    return {}

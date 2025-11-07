import logging
from typing import Dict, Any

from src.core.state import PRAnalysisState
from src.utils.azure_requests import AzureManager

logger = logging.getLogger(__name__)


def fetch_pr_data_node(state: PRAnalysisState) -> Dict[str, Any]:
    pr_id = state["pr_id"]
    logger.info(f"[NODE: fetch_pr_data] Starting to fetch PR #{pr_id}")
    pr_data = AzureManager.get_pr_details(pr_id)

    if pr_data is None:
        error_msg = f"Failed to fetch PR #{pr_id} details from Azure DevOps"
        logger.error(f"[NODE: fetch_pr_data] {error_msg}")

        return {"error": error_msg}

    logger.info(
        f"[NODE: fetch_pr_data] ✓ PR #{pr_id} fetched successfully: "
        f"{pr_data['total_commits']} commits, "
        f"{pr_data['summary']['total_files_changed']} files changed"
    )

    return {"pr_data": pr_data}

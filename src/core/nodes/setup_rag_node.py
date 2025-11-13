import logging
from typing import Dict, Any

from src.core.state import PRAnalysisState
from src.providers.rag_manager import RAGManager
from src.providers.tools import set_rag_manager
from src.utils.file_filters import filter_analyzable_files

logger = logging.getLogger(__name__)


def setup_rag_node(state: PRAnalysisState) -> Dict[str, Any]:
    pr_data = state.get("pr_data")
    pr_id = state.get("pr_id")

    if not pr_data:
        logger.error("[NODE: setup_rag] No pr_data in state, cannot create RAG")
        return {"error": "Missing pr_data for RAG creation"}

    logger.info(f"[NODE: setup_rag] Creating RAG for PR #{pr_id}")

    try:
        rag_manager = RAGManager()

        all_files = pr_data.get("files", [])
        analyzable_files, ignored_files = filter_analyzable_files(all_files)

        logger.info(
            f"[NODE: setup_rag] Filtered files: {len(analyzable_files)} to analyze, "
            f"{len(ignored_files)} ignored"
        )

        pr_data_filtered = pr_data.copy()
        pr_data_filtered["files"] = analyzable_files

        rag_manager.create_from_pr_data(pr_data_filtered, chunk_size=800)

        logger.info(f"[NODE: setup_rag] ✅ RAG created successfully")

        set_rag_manager(rag_manager)

        logger.info("[NODE: setup_rag] ✅ RAG injected into tools, ready for agents")

        return {"rag_created": True, "_rag_manager": rag_manager}

    except Exception as e:
        logger.error(f"[NODE: setup_rag] ❌ Error creating RAG: {e}", exc_info=True)
        return {"error": f"Failed to create RAG: {str(e)}", "rag_created": False}

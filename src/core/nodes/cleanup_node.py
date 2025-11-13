import logging
from typing import Dict, Any
from contextvars import ContextVar

from src.core.state import PRAnalysisState
from src.providers.tools.shared_tools import _rag_manager_ctx

logger = logging.getLogger(__name__)


def cleanup_resources_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: cleanup] Starting cleanup of resources")

    rag_manager = _rag_manager_ctx.get()

    if rag_manager is not None:
        try:
            rag_manager.cleanup()
            logger.info("[NODE: cleanup] ✅ RAG Manager cleaned successfully")
        except Exception as e:
            logger.error(f"[NODE: cleanup] ⚠️ Error cleaning RAG Manager: {e}")
    else:
        logger.info("[NODE: cleanup] No RAG Manager to cleanup")

    _rag_manager_ctx.set(None)
    logger.info("[NODE: cleanup] ✅ RAG Manager context cleared")

    logger.info("[NODE: cleanup] ✅ Cleanup complete")

    return {}
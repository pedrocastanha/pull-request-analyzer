import logging
from typing import Dict, Any

from src.core.state import PRAnalysisState
from src.utils.azure_requests import AzureManager

logger = logging.getLogger(__name__)


def publish_comments_node(state: PRAnalysisState) -> Dict[str, Any]:
    """
    Node final do LangGraph que publica comentários de análise no Azure DevOps PR.

    Este node:
    1. Recebe o state contendo todas as análises dos agentes
    2. Extrai os comentários/issues de cada análise
    3. Publica cada comentário como uma thread no Azure DevOps PR
    4. Retorna estatísticas de publicação

    Args:
        state: Estado do LangGraph contendo pr_id e todas as análises

    Returns:
        Dicionário com estatísticas de publicação para atualizar o state
    """
    logger.info("[NODE: publish_comments] Starting comment publication to Azure DevOps")

    pr_id = state.get("pr_id")

    if not pr_id:
        logger.error("[NODE: publish_comments] ❌ No PR ID found in state")
        return {
            "error": "No PR ID available for publishing comments"
        }

    # Monta o relatório de análise a partir do state
    # O state contém: security_analysis, performance_analysis, clean_code_analysis, etc.
    analysis_report = {
        "security_analysis": state.get("security_analysis"),
        "performance_analysis": state.get("performance_analysis"),
        "clean_code_analysis": state.get("clean_code_analysis"),
        "logical_analysis": state.get("logical_analysis"),
        "reviewer_analysis": state.get("reviewer_analysis"),
    }

    # Remove análises None/vazias
    analysis_report = {
        key: value
        for key, value in analysis_report.items()
        if value is not None
    }

    if not analysis_report:
        logger.warning("[NODE: publish_comments] ⚠️ No analyses found to publish")
        return {
            "publication_stats": {
                "total_comments": 0,
                "successful": 0,
                "failed": 0,
                "message": "No analyses to publish"
            }
        }

    logger.info(
        f"[NODE: publish_comments] Publishing comments from "
        f"{len(analysis_report)} agent analyses"
    )

    # Publica comentários usando o AzureManager
    publication_stats = AzureManager.publish_analysis_comments(
        pr_id=pr_id,
        analysis_report=analysis_report
    )

    logger.info(
        f"[NODE: publish_comments] ✅ Publication complete: "
        f"{publication_stats['successful']}/{publication_stats['total_comments']} "
        f"comments published successfully"
    )

    # Se houve falhas, loga detalhes
    if publication_stats['failed'] > 0:
        logger.warning(
            f"[NODE: publish_comments] ⚠️ {publication_stats['failed']} comments "
            f"failed to publish"
        )
        for error in publication_stats.get('errors', []):
            logger.debug(f"[NODE: publish_comments] Error detail: {error}")

    # Retorna estatísticas para atualizar o state
    return {
        "publication_stats": publication_stats
    }
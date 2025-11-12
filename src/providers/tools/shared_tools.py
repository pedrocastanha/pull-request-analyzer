import logging
from typing import Optional

from langchain_core.tools import tool
from src.utils.pinecone_manager import PineconeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_rag_manager = None

def set_rag_manager(rag_manager):
    global _rag_manager
    _rag_manager = rag_manager
    logger.info("[TOOLS] RAG Manager injected into tools")


@tool
def search_pr_code(query: str, top_k: int = 5, filter_extension: Optional[str] = None) -> str:
    global _rag_manager

    if _rag_manager is None:
        logger.error("[TOOL: search_pr_code] RAG Manager not initialized!")
        return "❌ Sistema de busca não está disponível. Informe ao desenvolvedor."

    try:
        logger.info(f"[TOOL: search_pr_code] Searching for: '{query}' (top_k={top_k}, filter={filter_extension})")

        result = _rag_manager.search(
            query=query,
            k=top_k,
            filter_extension=filter_extension
        )

        return result

    except Exception as e:
        logger.error(f"[TOOL: search_pr_code] Error: {e}")
        return f"❌ Erro ao buscar código: {str(e)}"


@tool
def search_informations(query: str, namespace: str) -> str:
    try:
        logger.info(f"[TOOL: search_informations] Searching in namespace='{namespace}' for query='{query}'")
        pinecone = PineconeManager(namespace)
        relevant_chunks = pinecone.search_documents(query, k=3)
        logger.info(f"[TOOL: search_informations] Found {len(relevant_chunks)} relevant document chunks")

        if not relevant_chunks:
            return f"Nenhuma informação encontrada para '{query}' no namespace '{namespace}'. Tente reformular a query ou verificar se o namespace está correto."

        return f"Informações encontradas para '{query}' (namespace: {namespace}):\n\n{relevant_chunks}"
    except Exception as e:
        logger.error(f"[TOOL: search_informations] Error searching: {e}")
        return f"Erro ao buscar informações: {str(e)}"

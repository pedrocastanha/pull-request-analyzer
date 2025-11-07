import logging

from langchain_core.tools import tool
from src.db.pinecone_manager import PineconeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
def search_informations(query: str, namespace: str) -> str:
    """Busca informações  """
    try:
        logger.info(f"Searching informations for {query}")
        pinecone = PineconeManager(namespace)
        relevant_chunks = pinecone.search_documents(query, k=3)
        logger.info(f"Found {len(relevant_chunks)} documents")

        return f"Informações encontradas para '{query}': {relevant_chunks}"
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise

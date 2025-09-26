import logging

from utils.pinecone_manager import PineconeManager
from langchain_core.tools import tool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

@tool
def search_informations(query: str, namespace: str) -> str:
    """
        Use esta ferramenta para pesquisar práticas recomendadas de programação, padrões de código e conceitos presentes nos livros mais renomados da área.
        java:
        padroes

    """
    try:
        logger.info(f"Searching informations for {query}")
        pinecone = PineconeManager(namespace)
        relevant_chunks = pinecone.search_documents(query, k=5)
        logger.info(f"Found {len(relevant_chunks)} documents")
        return f"Informações encontradas para '{query}': {relevant_chunks} ."
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return f"Error processing message: {e}"

tools_service = [search_informations]
import logging

from langchain_core.tools import tool
from src.utils.pinecone_manager import PineconeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@tool
def search_informations(query: str, namespace: str) -> str:
    """
    Esta tool acessa uma base de conhecimento vetorial (Pinecone) contendo conteúdo de livros
    técnicos especializados em diferentes áreas de engenharia de software.

    Args:
        query: Descrição do que você precisa buscar. Seja específico e use termos técnicos.
               Exemplo: "N+1 query problem e soluções com eager loading"

        namespace: Namespace da base de conhecimento a ser consultada. Valores válidos:
            - "security": Livros sobre segurança (OWASP, Secure Coding, etc.)
            - "performance": Livros sobre otimização e performance
            - "clean_code": Livros sobre Clean Code, SOLID, refactoring (Martin, Fowler, etc.)
            - "logical": Livros sobre debugging, análise lógica e edge cases

    Returns:
        String contendo os 3 trechos mais relevantes encontrados nos livros, ranqueados por
        similaridade semântica com a query. Use estas informações para validar suas análises.

    Quando usar:
        - Ao identificar um padrão suspeito e querer confirmar se é um problema conhecido
        - Para buscar a solução correta/recomendada para um problema específico
        - Quando tiver dúvida sobre boas práticas ou padrões
        - Para validar se sua análise está alinhada com a literatura técnica

    Exemplos de uso:
        search_informations("SQL injection prevenção prepared statements", "security")
        search_informations("complexidade ciclomática e refactoring", "clean_code")
        search_informations("race conditions em operações assíncronas", "logical")
    """
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

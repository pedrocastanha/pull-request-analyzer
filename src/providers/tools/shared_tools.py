import logging
from contextvars import ContextVar
from functools import lru_cache
from typing import Optional

from langchain_core.tools import tool
from src.utils.pinecone_manager import PineconeManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_rag_manager_ctx: ContextVar[Optional['RAGManager']] = ContextVar('rag_manager', default=None)


def set_rag_manager(rag_manager):
    _rag_manager_ctx.set(rag_manager)
    logger.info("[TOOLS] RAG Manager set for current context")


@tool
def search_pr_code(
    query: str, top_k: int = 5, filter_extension: Optional[str] = None
) -> str:
    """
    🔍 Busca trechos de código relevantes no PR atual usando busca semântica vetorial.

    QUANDO USAR:
    - Ao procurar código relacionado a um tópico específico
    - Para verificar se existem mudanças em determinada área
    - Antes de analisar, para encontrar trechos relevantes

    Args:
        query: Descrição do que você procura. Seja específico e use termos técnicos.
               Exemplos:
                 - "código que faz autenticação de usuários"
                 - "queries SQL ou acesso a banco de dados"
                 - "validação de entrada de usuários"
                 - "uso de bibliotecas de criptografia"

        top_k: Quantos trechos retornar (padrão: 5, máximo recomendado: 10)

        filter_extension: Filtrar por tipo de arquivo (opcional)
                         Exemplos: "py", "ts", "java", "js"

    Returns:
        String contendo os trechos de código mais relevantes encontrados,
        com informações do arquivo, linhas modificadas e o diff.

    IMPORTANTE:
    - Esta tool busca APENAS no código do PR atual (não em livros técnicos)
    - Para buscar em livros técnicos, use search_informations
    - Faça queries ESPECÍFICAS para melhores resultados
    - Se não encontrar nada, tente reformular a query

    Exemplos de uso:
        search_pr_code("autenticação com JWT ou tokens")
        search_pr_code("loops aninhados ou iterações", top_k=3)
        search_pr_code("imports de bibliotecas de segurança", filter_extension="py")
    """
    rag_manager = _rag_manager_ctx.get()

    if rag_manager is None:
        logger.error("[TOOL: search_pr_code] RAG Manager not initialized!")
        return "❌ Sistema de busca não está disponível. Informe ao desenvolvedor."

    try:
        logger.info(
            f"[TOOL: search_pr_code] Searching for: '{query}' (top_k={top_k}, filter={filter_extension})"
        )

        result = rag_manager.search(
            query=query, k=top_k, filter_extension=filter_extension
        )

        return result

    except Exception as e:
        logger.error(f"[TOOL: search_pr_code] Error: {e}")
        return f"❌ Erro ao buscar código: {str(e)}"


@lru_cache(maxsize=4)
def _get_pinecone_manager(namespace: str) -> PineconeManager:
    logger.info(f"[PINECONE] Creating new manager for namespace: {namespace}")
    return PineconeManager(namespace)


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
        logger.info(
            f"[TOOL: search_informations] Searching in namespace='{namespace}' for query='{query}'"
        )
        pinecone = _get_pinecone_manager(namespace)
        relevant_chunks = pinecone.search_documents(query, k=3)
        logger.info(
            f"[TOOL: search_informations] Found {len(relevant_chunks)} relevant document chunks"
        )

        if not relevant_chunks:
            return f"Nenhuma informação encontrada para '{query}' no namespace '{namespace}'. Tente reformular a query ou verificar se o namespace está correto."

        return f"Informações encontradas para '{query}' (namespace: {namespace}):\n\n{relevant_chunks}"
    except Exception as e:
        logger.error(f"[TOOL: search_informations] Error searching: {e}")
        return f"Erro ao buscar informações: {str(e)}"

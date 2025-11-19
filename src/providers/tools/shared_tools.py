import logging
import os
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


def _search_pr_code_impl(
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


@tool
def search_pr_code(query: str = "", top_k: int = 5, filter_extension: Optional[str] = None, **kwargs) -> str:
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
    if 'query=' in kwargs:
        query = kwargs['query=']

    if not query:
        return "❌ Parâmetro 'query' é obrigatório"

    return _search_pr_code_impl(query=query, top_k=top_k, filter_extension=filter_extension)


@lru_cache(maxsize=4)
def _get_pinecone_manager(namespace: str) -> PineconeManager:
    logger.info(f"[PINECONE] Creating new manager for namespace: {namespace}")
    return PineconeManager(namespace)


@tool
def search_knowledge(query: str, namespace: str) -> str:
    """
    Esta tool é a sua base de conhecimento técnico contendo conteúdo de livros
    técnicos mais famosos e especializados em diferentes áreas de engenharia de software.

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

        return f"Informações encontradas para '{query}':\n\n{relevant_chunks}"
    except Exception as e:
        logger.error(f"[TOOL: search_informations] Error searching: {e}")
        return f"Erro ao buscar informações: {str(e)}"


def _search_file_content_impl(file_path: str, line_number: int, context_lines: int = 5) -> str:
    try:
        if not os.path.exists(file_path):
            return f"❌ Erro: Arquivo não encontrado: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        actual_line_index = line_number - 1

        if not (0 <= actual_line_index < len(lines)):
            return f"❌ Erro: Número de linha inválido ({line_number}) para o arquivo {file_path}. O arquivo tem {len(lines)} linhas."

        start_line = max(0, actual_line_index - context_lines)
        end_line = min(len(lines), actual_line_index + context_lines + 1)

        snippet = []
        for i in range(start_line, end_line):
            snippet.append(f"{i + 1:4d}| {lines[i].rstrip()}")

        return (
            f"Conteúdo do arquivo {file_path} em torno da linha {line_number}:\n"
            f"```\n"
            f"{ '\n'.join(snippet)}\n"
            f"```"
        )

    except Exception as e:
        logger.error(f"[TOOL: search_file_content] Error reading file {file_path}: {e}")
        return f"❌ Erro ao ler o arquivo {file_path}: {str(e)}"

@tool
def search_file_content_tool(file_path: str, line_number: int, context_lines: int = 5) -> str:
    """
    🔍 Busca o conteúdo de um arquivo em torno de um número de linha específico.

    QUANDO USAR:
    - Para obter o contexto exato do código ao validar um comentário.
    - Para verificar se uma correção ou problema apontado pelo Reviewer Agent realmente existe.

    Args:
        file_path: O caminho completo ou relativo para o arquivo.
        line_number: O número da linha (1-baseado) para focar a busca.
        context_lines: Opcional. Número de linhas a serem incluídas antes e depois da linha principal. Padrão é 5.

    Returns:
        Um snippet do código com números de linha, incluindo o contexto,
        ou uma mensagem de erro se o arquivo não for encontrado ou a linha for inválida.

    Exemplos de uso:
        search_file_content_tool("src/service/UserService.java", 123)
        search_file_content_tool("config/app.py", 45, context_lines=3)
    """
    return _search_file_content_impl(file_path, line_number, context_lines)
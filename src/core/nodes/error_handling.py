import logging
from typing import Dict, Any

from src.core.state import PRAnalysisState
from src.providers.agents import AgentManager
from src.providers.tools.shared_tools import (
    search_knowledge,
    search_pr_code,
    search_knowledge,
    search_pr_code,
    search_web_docs,
    set_rag_manager,
)
from src.utils.diff_parser import DiffParser
from src.utils.file_filter import FileFilter
from src.utils.cosmetic_filter import filter_cosmetic_only_files
from src.schemas import ErrorHandlingResponse
from src.utils.callbacks import ToolMonitorCallback
from src.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


async def error_handling_analyst_node(state: PRAnalysisState) -> Dict[str, Any]:
    """
    Error Handling Analyst Node - Analisa tratamento de erros do PR
    """
    logger.info("[NODE: error_handling_analyst] Iniciando análise de Error Handling")

    rag_manager = state.get("_rag_manager")
    if rag_manager:
        set_rag_manager(rag_manager)

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Não é possível analisar Error Handling: pr_data is None"
        logger.error(f"[NODE: error_handling_analyst] {error_msg}")
        return {"error": [error_msg]}

    pr_id = pr_data["pr_id"]
    all_files = pr_data["files"]

    # PASSO 1: Filtra arquivos irrelevantes para o agente
    files_for_agent = FileFilter.filter_files_for_agent(all_files, "ErrorHandlingAnalyst")

    # PASSO 2: Filtra arquivos com APENAS mudanças cosméticas
    files, cosmetic_skipped = filter_cosmetic_only_files(files_for_agent)
    total_files = len(files)

    if cosmetic_skipped > 0:
        logger.info(
            f"[NODE: error_handling_analyst] ⚡ Filtrados {cosmetic_skipped} arquivo(s) "
            f"com apenas mudanças cosméticas"
        )

    if total_files == 0:
        logger.info(
            f"[NODE: error_handling_analyst] ✓ PR #{pr_id} - Nenhum arquivo com mudanças "
            f"significativas para analisar"
        )
        return {"error_handling_analysis": {"issues": [], "summary": "Apenas mudanças cosméticas detectadas"}}

    logger.info(
        f"[NODE: error_handling_analyst] Analisando PR #{pr_id} "
        f"({total_files} arquivos, +{pr_data['total_additions']}/-{pr_data['total_deletions']} linhas)"
    )

    context = _build_context(pr_data, files)

    try:
        callback = ToolMonitorCallback(verbose=True)

        project_type = state.get("project_type", "java")
        agent = AgentManager.get_agents(
            tools=[search_knowledge, search_pr_code, search_web_docs],
            agent_name="ErrorHandlingAnalyst",
            project_type=project_type,
        )

        response = await agent.ainvoke(
            {"context": context}, config={"callbacks": [callback]}
        )

        callback.print_summary()

        if isinstance(response, dict) and "output" in response:
            analysis_text = response["output"]
        elif hasattr(response, "content"):
            analysis_text = (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            )
        else:
            analysis_text = str(response)

        parsed_data = parse_llm_json_response(analysis_text)

        analyst_response = ErrorHandlingResponse(**parsed_data)

        logger.info(
            f"[NODE: error_handling_analyst] ✓ Encontrados {len(analyst_response.issues)} problemas potenciais"
        )

        return {"error_handling_analyst_output": analyst_response.model_dump()}

    except Exception as e:
        error_msg = f"Erro durante análise de error handling: {str(e)}"
        logger.error(f"[NODE: error_handling_analyst] {error_msg}", exc_info=True)
        return {"error": [error_msg]}


def _build_context(pr_data: Dict[str, Any], files: list) -> str:
    """Constrói contexto para análise de error handling"""
    context_parts = []
    context_parts.append(
        f"# Pull Request #{pr_data['pr_id']} - Análise de Error Handling\n"
    )
    context_parts.append(
        f"Total de arquivos modificados: {pr_data['total_files']} "
        f"(+{pr_data['total_additions']} -{pr_data['total_deletions']} linhas)\n"
    )

    context_parts.append("\n## Arquivos Modificados:\n")

    for file_change in files:
        context_parts.append(
            f"  • {file_change['path']} ({file_change['change_type']}) "
            f"+{file_change['additions']} -{file_change['deletions']}"
        )
        context_parts.append(
            f"\n```diff\n{DiffParser.annotate_diff_with_lines(file_change['diff'])}\n```"
        )

    context_parts.append(
        "\nUse a ferramenta search_pr_code() para buscar padrões específicos no código!"
    )
    context_parts.append(
        "\n⚠️ ALTA TOLERÂNCIA (NOISE REDUCTION):"
        "\n- IGNORE falta de try-catch em métodos CRUD simples."
        "\n- IGNORE exceções genéricas se houver um Global Exception Handler."
        "\n- REPORTE APENAS: Exceções engolidas (pass), stack traces expostos, ou falhas que derrubam a aplicação."
    )

    return "\n".join(context_parts)

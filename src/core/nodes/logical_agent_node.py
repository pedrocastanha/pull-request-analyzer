import logging
from typing import Dict, Any
from pydantic import ValidationError

from src.core import PRAnalysisState
from src.providers import AgentManager
from src.providers.tools.shared_tools import search_knowledge, search_pr_code, search_web_docs
from src.schemas import LogicalAnalysis
from src.utils.json_parser import parse_llm_json_response
from src.utils.issue_classifier import IssueClassifier
from src.utils.diff_parser import DiffParser
from src.utils.file_filter import FileFilter
from src.utils.cosmetic_filter import filter_cosmetic_only_files

logger = logging.getLogger(__name__)

_classifier = None


async def logical_analysis_node(state: PRAnalysisState) -> Dict[str, Any]:
    from src.providers.tools import set_rag_manager

    rag_manager = state.get("_rag_manager")
    if rag_manager:
        set_rag_manager(rag_manager)

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Cannot analyze logical: pr_data is None"
        logger.error(f"[NODE: logical_analysis] {error_msg}")
        return {"error": [error_msg]}

    pr_id = pr_data["pr_id"]
    all_files = pr_data["files"]

    # PASSO 1: Filtra arquivos irrelevantes para o agente
    files_for_agent = FileFilter.filter_files_for_agent(all_files, "Logical")

    # PASSO 2: Filtra arquivos com APENAS mudanças cosméticas
    files, cosmetic_skipped = filter_cosmetic_only_files(files_for_agent)
    total_files = len(files)

    if cosmetic_skipped > 0:
        logger.info(
            f"[NODE: logical_analysis] ⚡ Filtrados {cosmetic_skipped} arquivo(s) "
            f"com apenas mudanças cosméticas"
        )

    if total_files == 0:
        logger.info(
            f"[NODE: logical_analysis] ✓ PR #{pr_id} - Nenhum arquivo com mudanças "
            f"significativas para analisar"
        )
        return {"logical_analysis": {"issues": [], "summary": "Apenas mudanças cosméticas detectadas"}}

    logger.info(
        f"[NODE: logical_analysis] Analyzing PR #{pr_id} "
        f"({total_files} files, +{pr_data['total_additions']}/-{pr_data['total_deletions']} lines)"
    )

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Análise Lógica\n")
    context_parts.append(
        f"Total de arquivos modificados: {total_files} "
        f"(+{pr_data['total_additions']} -{pr_data['total_deletions']} linhas)\n"
    )

    for file_change in files:
        context_parts.append(f"\n## Arquivo: {file_change['path']}")
        context_parts.append(f"Tipo de mudança: {file_change['change_type']}")
        context_parts.append(
            f"Linhas: +{file_change['additions']} -{file_change['deletions']}"
        )
        context_parts.append(
            f"\n```diff\n{DiffParser.annotate_diff_with_lines(file_change['diff'])}\n```"
        )

    context_parts.append(
        "\n🧠 LÓGICA RIGOROSA:"
        "\n- NÃO reporte 'código confuso' (subjetivo)."
        "\n- REPORTE: Race Conditions, Edge Cases não tratados (null, vazio, negativo), Lógica Booleana errada."
        "\n- PROVE o erro lógico com um contra-exemplo."
        "\n- Use search_web_docs() para verificar comportamentos de bibliotecas."
    )

    context = "\n".join(context_parts)

    try:
        callback = AgentManager.get_callback(verbose=True)

        project_type = state.get("project_type", "java")
        agent = AgentManager.get_agents(
            tools=[search_knowledge, search_pr_code, search_web_docs],
            agent_name="Logical",
            project_type=project_type,
        )

        response = await agent.ainvoke(
            {"context": context}, config={"callbacks": [callback]}
        )

        callback.print_summary()

        if isinstance(response, dict) and "output" in response:
            analysis_text = response["output"]
        elif hasattr(response, "content"):
            if isinstance(response.content, list):
                analysis_text = str(response.content)
            else:
                analysis_text = response.content
        else:
            analysis_text = str(response)

        parsed_data = parse_llm_json_response(analysis_text)

        try:
            analysis_result = LogicalAnalysis(**parsed_data)
        except ValidationError as e:
            logger.warning(
                f"[NODE: logical_analysis] Validation error, using fallback: {e}"
            )
            analysis_result = LogicalAnalysis(issues=[], summary="Validation failed")

        for issue in analysis_result.issues:
            issue.agent_type = "Logical"

        issues_count = len(analysis_result.issues)
        logger.info(
            f"[NODE: logical_analysis] ✓ Analysis complete. "
            f"Found {issues_count} logical issue(s)"
        )

        if issues_count > 0:
            try:
                global _classifier
                if _classifier is None:
                    _classifier = IssueClassifier()

                code_context_parts = []
                for file_change in files[:10]:
                    code_context_parts.append(
                        f"File: {file_change['path']}\n"
                        f"Changes: +{file_change['additions']} -{file_change['deletions']}\n"
                    )
                code_context = "\n".join(code_context_parts)

                issues_dict = [
                    issue.model_dump() if hasattr(issue, "model_dump") else issue
                    for issue in analysis_result.issues
                ]
                classified_issues = _classifier.classify_issues(
                    agent_type="logical",
                    issues=issues_dict,
                    code_context=code_context,
                )

                problem_count = sum(
                    1 for i in classified_issues if i.get("category") == "PROBLEM"
                )
                suggestion_count = sum(
                    1 for i in classified_issues if i.get("category") == "SUGGESTION"
                )
                logger.info(
                    f"[NODE: logical_analysis] Classification: "
                    f"{problem_count} PROBLEM, {suggestion_count} SUGGESTION"
                )

                return {
                    "logical_analysis": {
                        "issues": classified_issues,
                        "summary": analysis_result.summary,
                    }
                }

            except Exception as e:
                logger.warning(f"[NODE: logical_analysis] Classification skipped: {e}")

        return {"logical_analysis": analysis_result.model_dump()}
    except Exception as e:
        error_msg = f"Error during logical analysis: {str(e)}"
        logger.error(f"[NODE: logical_analysis] {error_msg}")
        return {"error": [error_msg]}

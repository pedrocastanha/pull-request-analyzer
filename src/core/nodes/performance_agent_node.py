import logging
from typing import Dict, Any

from src.core import PRAnalysisState
from src.providers import AgentManager
from src.providers.tools.shared_tools import search_informations, search_pr_code
from src.utils.json_parser import parse_llm_json_response
from src.utils.issue_classifier import IssueClassifier

logger = logging.getLogger(__name__)

_classifier = None


async def performance_analysis_node(state: PRAnalysisState) -> Dict[str, Any]:
    from src.providers.tools import set_rag_manager
    rag_manager = state.get("_rag_manager")
    if rag_manager:
        set_rag_manager(rag_manager)

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Cannot analyze performance: pr_data is None"
        logger.error(f"[NODE: performance_analysis] {error_msg}")
        return {"error": error_msg}

    pr_id = pr_data["pr_id"]
    total_files = pr_data["total_files"]
    files = pr_data["files"]

    logger.info(
        f"[NODE: performance_analysis] Analyzing PR #{pr_id} "
        f"({total_files} files, +{pr_data['total_additions']}/-{pr_data['total_deletions']} lines)"
    )

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Análise de Performance\n")
    context_parts.append(
        f"Total de arquivos modificados: {total_files} "
        f"(+{pr_data['total_additions']} -{pr_data['total_deletions']} linhas)\n"
    )
    context_parts.append("\n## Arquivos Modificados:\n")

    for file_change in files:
        context_parts.append(
            f"  • {file_change['path']} ({file_change['change_type']}) "
            f"+{file_change['additions']} -{file_change['deletions']}"
        )

    context_parts.append(
        "\n💡 Use a tool `search_pr_code()` para buscar trechos específicos do código!"
    )

    context = "\n".join(context_parts)

    try:
        callback = AgentManager.get_callback(verbose=True)

        agent = AgentManager.get_agents(
            tools=[search_informations, search_pr_code], agent_name="Performance"
        )

        logger.info(
            f"[NODE: performance_analysis] Invoking agent with context size: {len(context)} chars"
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

        analysis_result = parse_llm_json_response(analysis_text)

        issues_count = (
            len(analysis_result.get("issues", []))
            if isinstance(analysis_result.get("issues"), list)
            else 0
        )
        logger.info(
            f"[NODE: performance_analysis] ✓ Analysis complete. "
            f"Found {issues_count} performance issue(s)"
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

                issues = analysis_result.get("issues", [])
                classified_issues = _classifier.classify_issues(
                    agent_type="performance",
                    issues=issues,
                    code_context=code_context,
                )
                analysis_result["issues"] = classified_issues

                problem_count = sum(1 for i in classified_issues if i.get('category') == 'PROBLEM')
                suggestion_count = sum(1 for i in classified_issues if i.get('category') == 'SUGGESTION')
                logger.info(
                    f"[NODE: performance_analysis] 🏷️ Classification: "
                    f"{problem_count} PROBLEM, {suggestion_count} SUGGESTION"
                )

            except Exception as e:
                logger.warning(f"[NODE: performance_analysis] ⚠️ Classification skipped: {e}")

        return {"performance_analysis": analysis_result}
    except Exception as e:
        error_msg = f"Error during performance analysis: {str(e)}"
        logger.error(f"[NODE: performance_analysis] {error_msg}")
        return {"error": error_msg}

import logging
import json
from typing import Dict, Any

from src.core.state import PRAnalysisState
from src.providers.agents import AgentManager
from src.providers.tools.shared_tools import search_informations

from src.providers.prompts.security import Security

logger = logging.getLogger(__name__)


async def security_analysis_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: security_analysis] Starting security analysis")

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Cannot analyze security: pr_data is None"
        logger.error(f"[NODE: security_analysis] {error_msg}")
        return {"error": error_msg}

    pr_id = pr_data["pr_id"]
    total_commits = pr_data["total_commits"]
    commits = pr_data["commits"]

    logger.info(
        f"[NODE: security_analysis] Analyzing PR #{pr_id} "
        f"({total_commits} commits, {pr_data['summary']['total_files_changed']} files)"
    )

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Análise de Segurança\n")
    context_parts.append(f"Total de commits: {total_commits}")
    context_parts.append(
        f"Total de arquivos modificados: {pr_data['summary']['total_files_changed']}\n"
    )

    for commit in commits:
        context_parts.append(f"\n## Commit: {commit['commit_id'][:8]}")
        context_parts.append(f"Autor: {commit.get('author', 'Unknown')}")
        context_parts.append(f"Mensagem: {commit.get('comment', 'No message')}\n")

        for file_change in commit["files_changed"]:
            context_parts.append(f"\n### Arquivo: {file_change['path']}")
            context_parts.append(f"Tipo de mudança: {file_change['change_type']}")
            context_parts.append(
                f"Linhas: +{file_change['additions']} -{file_change['deletions']}"
            )
            context_parts.append(f"\n```diff\n{file_change['diff']}\n```")

    context = "\n".join(context_parts)

    try:
        agent = AgentManager.get_agents(
            tools=[search_informations], agent_name="Security"
        )
        response = await agent.ainvoke({"context": context})

        if hasattr(response, "content"):
            if isinstance(response.content, list):
                analysis_text = str(response.content)
            else:
                analysis_text = response.content
        else:
            analysis_text = str(response)

        try:
            analysis_result = json.loads(analysis_text)
        except (json.JSONDecodeError, AttributeError, TypeError):
            analysis_result = {"raw_analysis": str(analysis_text), "format": "text"}

        logger.info(
            f"[NODE: security_analysis] ✓ Analysis complete. "
            f"Result preview: {str(analysis_result)[:300]}..."
        )

        return {"security_analysis": analysis_result}
    except Exception as e:
        error_msg = f"Error during security analysis: {str(e)}"
        logger.error(f"[NODE: security_analysis] {error_msg}")
        return {"error": error_msg}

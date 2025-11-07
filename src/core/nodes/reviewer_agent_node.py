import json
import logging
from typing import Dict, Any

from src.core import PRAnalysisState
from src.providers import AgentManager

logger = logging.getLogger(__name__)


async def reviewer_analysis_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: reviewer_analysis] Starting review of all analyses")

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Cannot review: pr_data is None"
        logger.error(f"[NODE: reviewer_analysis] {error_msg}")
        return {"error": error_msg}

    security_analysis = state.get("security_analysis")
    performance_analysis = state.get("performance_analysis")
    clean_code_analysis = state.get("clean_code_analysis")
    logical_analysis = state.get("logical_analysis")

    pr_id = pr_data["pr_id"]

    logger.info(
        f"[NODE: reviewer_analysis] Reviewing PR #{pr_id} - "
        f"Analyses available: Security={security_analysis is not None}, "
        f"Performance={performance_analysis is not None}, "
        f"CleanCode={clean_code_analysis is not None}, "
        f"Logical={logical_analysis is not None}"
    )

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Review Final\n")
    context_parts.append("## Análises Disponíveis:\n")

    if security_analysis:
        context_parts.append("### 🔒 Security Analysis:")
        context_parts.append(
            f"```json\n{json.dumps(security_analysis, indent=2)}\n```\n"
        )

    if performance_analysis:
        context_parts.append("### ⚡ Performance Analysis:")
        context_parts.append(
            f"```json\n{json.dumps(performance_analysis, indent=2)}\n```\n"
        )

    if clean_code_analysis:
        context_parts.append("### ✨ Clean Code Analysis:")
        context_parts.append(
            f"```json\n{json.dumps(clean_code_analysis, indent=2)}\n```\n"
        )

    if logical_analysis:
        context_parts.append("### 🧠 Logical Analysis:")
        context_parts.append(
            f"```json\n{json.dumps(logical_analysis, indent=2)}\n```\n"
        )

    context_parts.append("\n## Tarefa:")
    context_parts.append(
        "Revise todas as análises acima. Se estiver satisfeito, retorne 'END'. "
        "Se precisar de mais informações de um agent específico, retorne o nome do agent: "
        "'security_agent', 'performance_agent', 'clean_coder_agent', ou 'logical_agent'."
    )

    context = "\n".join(context_parts)

    try:
        agent = AgentManager.get_agents(tools=[], agent_name="Reviewer")
        response = await agent.ainvoke({"context": context})

        analysis_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        next_node = "END"

        analysis_text_lower = analysis_text.lower()
        if "security_agent" in analysis_text_lower or "security" in analysis_text_lower:
            next_node = "security_agent"
        elif (
            "performance_agent" in analysis_text_lower
            or "performance" in analysis_text_lower
        ):
            next_node = "performance_agent"
        elif (
            "clean_coder_agent" in analysis_text_lower or "clean" in analysis_text_lower
        ):
            next_node = "clean_coder_agent"
        elif "logical_agent" in analysis_text_lower or "logical" in analysis_text_lower:
            next_node = "logical_agent"

        logger.info(f"[NODE: reviewer_analysis] Decision: next_node={next_node}")

        return {
            "reviewer_analysis": {"review": analysis_text, "decision": next_node},
            "next_node": next_node,
        }

    except Exception as e:
        error_msg = f"Error during reviewer analysis: {str(e)}"
        logger.error(f"[NODE: reviewer_analysis] {error_msg}")
        return {"error": error_msg}

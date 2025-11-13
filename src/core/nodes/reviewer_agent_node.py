import json
import logging
from typing import Dict, Any

from src.core import PRAnalysisState
from src.providers import AgentManager
from src.utils.json_parser import parse_llm_json_response

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

    def extract_essential_fields(analysis):
        if not isinstance(analysis, dict) or "issues" not in analysis:
            return analysis

        essential_issues = []
        for issue in analysis.get("issues", []):
            essential_issues.append({
                "title": issue.get("title"),
                "description": issue.get("description"),
                "severity": issue.get("severity"),
                "file": issue.get("file"),
                "line": issue.get("line"),
                "impact": issue.get("impact"),
                "evidence": issue.get("evidence"),
                "example": issue.get("example")
            })

        return {
            "issues": essential_issues,
            "summary": analysis.get("summary")
        }

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Review Final\n")
    context_parts.append("## Análises Disponíveis:\n")

    if security_analysis:
        context_parts.append("### 🔒 Security Analysis:")
        essential_security = extract_essential_fields(security_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_security, indent=2) + "\n```\n"
        )

    if performance_analysis:
        context_parts.append("### ⚡ Performance Analysis:")
        essential_performance = extract_essential_fields(performance_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_performance, indent=2) + "\n```\n"
        )

    if clean_code_analysis:
        context_parts.append("### ✨ Clean Code Analysis:")
        essential_clean_code = extract_essential_fields(clean_code_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_clean_code, indent=2) + "\n```\n"
        )

    if logical_analysis:
        context_parts.append("### 🧠 Logical Analysis:")
        essential_logical = extract_essential_fields(logical_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_logical, indent=2) + "\n```\n"
        )

    context_parts.append("\n## Tarefa:")
    context_parts.append(
        "Analise todas as informações acima e gere comentários estruturados "
        "por arquivo e linha para cada issue encontrado pelos agents. "
        "Consolide issues duplicados e crie um relatório final."
    )

    context = "\n".join(context_parts)

    try:
        callback = AgentManager.get_callback(verbose=True)

        agent = AgentManager.get_agents(tools=[], agent_name="Reviewer")

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

        comments_count = (
            len(analysis_result.get("comments", []))
            if isinstance(analysis_result.get("comments"), list)
            else 0
        )
        logger.info(
            f"[NODE: reviewer_analysis] ✓ Generated {comments_count} comment(s)"
        )

        return {"reviewer_analysis": analysis_result}

    except Exception as e:
        error_msg = f"Error during reviewer analysis: {str(e)}"
        logger.error(f"[NODE: reviewer_analysis] {error_msg}")
        return {"error": error_msg}

import json
import logging
from typing import Dict, Any

from src.core import PRAnalysisState
from src.providers import AgentManager
from src.providers.llms import LLMManager
from src.providers.prompts_manager import PromptManager
from src.schemas import ReviewerAnalysis
from src.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


async def reviewer_analysis_node(state: PRAnalysisState) -> Dict[str, Any]:
    logger.info("[NODE: reviewer_analysis] Starting review of all analyses")

    pr_data = state.get("pr_data")
    if pr_data is None:
        error_msg = "Cannot review: pr_data is None"
        logger.error(f"[NODE: reviewer_analysis] {error_msg}")
        return {"error": [error_msg]}

    security_analysis = state.get("security_analysis")
    performance_analysis = state.get("performance_analysis")
    clean_code_analysis = state.get("clean_code_analysis")
    logical_analysis = state.get("logical_analysis")
    api_design_analysis = state.get("api_design_analyst_output")
    error_handling_analysis = state.get("error_handling_analyst_output")

    pr_id = pr_data["pr_id"]

    def count_issues_by_priority(analysis):
        if not isinstance(analysis, dict) or "issues" not in analysis:
            return {"total": 0, "critica": 0, "alta": 0, "media": 0, "baixa": 0}

        issues = analysis.get("issues", [])
        critica = sum(1 for i in issues if i.get("priority") == "Crítica")
        alta = sum(1 for i in issues if i.get("priority") == "Alta")
        media = sum(1 for i in issues if i.get("priority") == "Média")
        baixa = sum(1 for i in issues if i.get("priority") == "Baixa")

        return {
            "total": len(issues),
            "critica": critica,
            "alta": alta,
            "media": media,
            "baixa": baixa,
        }

    security_counts = count_issues_by_priority(security_analysis)
    performance_counts = count_issues_by_priority(performance_analysis)
    clean_code_counts = count_issues_by_priority(clean_code_analysis)
    logical_counts = count_issues_by_priority(logical_analysis)
    api_design_counts = count_issues_by_priority(api_design_analysis)
    error_handling_counts = count_issues_by_priority(error_handling_analysis)

    total_critica = (
        security_counts["critica"]
        + performance_counts["critica"]
        + clean_code_counts["critica"]
        + logical_counts["critica"]
        + api_design_counts["critica"]
        + error_handling_counts["critica"]
    )
    total_alta = (
        security_counts["alta"]
        + performance_counts["alta"]
        + clean_code_counts["alta"]
        + logical_counts["alta"]
        + api_design_counts["alta"]
        + error_handling_counts["alta"]
    )
    total_media = (
        security_counts["media"]
        + performance_counts["media"]
        + clean_code_counts["media"]
        + logical_counts["media"]
        + api_design_counts["media"]
        + error_handling_counts["media"]
    )
    total_baixa = (
        security_counts["baixa"]
        + performance_counts["baixa"]
        + clean_code_counts["baixa"]
        + logical_counts["baixa"]
        + api_design_counts["baixa"]
        + error_handling_counts["baixa"]
    )

    logger.info(
        f"[NODE: reviewer_analysis] Reviewing PR #{pr_id} - "
        f"Security: {security_counts['total']}, "
        f"Performance: {performance_counts['total']}, "
        f"CleanCode: {clean_code_counts['total']}, "
        f"Logical: {logical_counts['total']}, "
        f"API Design: {api_design_counts['total']}, "
        f"Error Handling: {error_handling_counts['total']}"
    )
    logger.info(
        f"Crítica={total_critica} | "
        f"Alta={total_alta} | "
        f"Média={total_media} | "
        f"Baixa={total_baixa}"
    )

    def extract_essential_fields(analysis):
        if not isinstance(analysis, dict) or "issues" not in analysis:
            return analysis

        essential_issues = []
        for issue in analysis.get("issues", []):
            essential_issues.append(
                {
                    "title": issue.get("title"),
                    "description": issue.get("description"),
                    "priority": issue.get("priority", "Baixa"),
                    "agent_type": issue.get("agent_type", "Unknown"),
                    "file": issue.get("file"),
                    "line": issue.get("line"),
                    "final_line": issue.get("final_line"),
                    "impact": issue.get("impact"),
                    "evidence": issue.get("evidence"),
                    "recommendation": issue.get("recommendation"),
                    "example": issue.get("example"),
                }
            )

        return {"issues": essential_issues, "summary": analysis.get("summary")}

    context_parts = []
    context_parts.append(f"# Pull Request #{pr_id} - Review Final\n")
    context_parts.append("## Análises Disponíveis:\n")

    if security_analysis:
        context_parts.append("###  Security Analysis:")
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
        context_parts.append("###  Logical Analysis:")
        essential_logical = extract_essential_fields(logical_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_logical, indent=2) + "\n```\n"
        )

    if api_design_analysis:
        context_parts.append("### 🎨 API Design Analysis:")
        essential_api_design = extract_essential_fields(api_design_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_api_design, indent=2) + "\n```\n"
        )

    if error_handling_analysis:
        context_parts.append("### ⚠️ Error Handling Analysis:")
        essential_error_handling = extract_essential_fields(error_handling_analysis)
        context_parts.append(
            "```json\n" + json.dumps(essential_error_handling, indent=2) + "\n```\n"
        )

    context_parts.append("\n## Tarefa:")
    context_parts.append(
        "Analise todas as informações acima e gere comentários estruturados "
        "por arquivo e linha para cada issue encontrado pelos agents. "
        "Consolide issues duplicados e crie um relatório final."
    )

    context = "\n".join(context_parts)

    try:
        project_type = state.get("project_type", "java")
        prompt = PromptManager.get_agent_prompt("Reviewer", project_type)
        structured_llm = LLMManager.get_structured_llm("gpt-4.1-mini", ReviewerAnalysis)

        chain = prompt | structured_llm

        analysis_result: ReviewerAnalysis = await chain.ainvoke({"context": context})

        comments_count = len(analysis_result.comments)
        logger.info(
            f"[NODE: reviewer_analysis] ✓ Generated {comments_count} comment(s)"
        )

        return {"reviewer_analysis": analysis_result.model_dump()}

    except Exception as e:
        error_msg = f"Error during reviewer analysis: {str(e)}"
        logger.error(f"[NODE: reviewer_analysis] {error_msg}")
        return {"error": [error_msg]}

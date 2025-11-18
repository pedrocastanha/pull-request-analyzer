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
        return {"error": error_msg}

    security_analysis = state.get("security_analysis")
    performance_analysis = state.get("performance_analysis")
    clean_code_analysis = state.get("clean_code_analysis")
    logical_analysis = state.get("logical_analysis")

    pr_id = pr_data["pr_id"]

    def count_issues_by_category(analysis):
        if not isinstance(analysis, dict) or "issues" not in analysis:
            return {"total": 0, "problems": 0, "suggestions": 0}

        issues = analysis.get("issues", [])
        problems = sum(1 for i in issues if i.get("category") == "PROBLEM")
        suggestions = sum(1 for i in issues if i.get("category") == "SUGGESTION")

        return {
            "total": len(issues),
            "problems": problems,
            "suggestions": suggestions
        }

    security_counts = count_issues_by_category(security_analysis)
    performance_counts = count_issues_by_category(performance_analysis)
    clean_code_counts = count_issues_by_category(clean_code_analysis)
    logical_counts = count_issues_by_category(logical_analysis)

    total_problems = (
        security_counts["problems"] +
        performance_counts["problems"] +
        clean_code_counts["problems"] +
        logical_counts["problems"]
    )
    total_suggestions = (
        security_counts["suggestions"] +
        performance_counts["suggestions"] +
        clean_code_counts["suggestions"] +
        logical_counts["suggestions"]
    )

    logger.info(
        f"[NODE: reviewer_analysis] Reviewing PR #{pr_id} - "
        f"Security: {security_counts['total']} ({security_counts['problems']}P/{security_counts['suggestions']}S), "
        f"Performance: {performance_counts['total']} ({performance_counts['problems']}P/{performance_counts['suggestions']}S), "
        f"CleanCode: {clean_code_counts['total']} ({clean_code_counts['problems']}P/{clean_code_counts['suggestions']}S), "
        f"Logical: {logical_counts['total']} ({logical_counts['problems']}P/{logical_counts['suggestions']}S)"
    )
    logger.info(
        f"[NODE: reviewer_analysis] 📊 Total: {total_problems} PROBLEMS, {total_suggestions} SUGGESTIONS"
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
                "category": issue.get("category", "SUGGESTION"),
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
        prompt = PromptManager.get_agent_prompt("Reviewer")
        structured_llm = LLMManager.get_structured_llm("gpt-4o-mini", ReviewerAnalysis)

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
        return {"error": error_msg}

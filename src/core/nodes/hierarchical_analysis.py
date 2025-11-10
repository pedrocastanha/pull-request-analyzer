import logging
from typing import Dict, List, Any

from src.core.states import HierarchicalPRAnalysisState, FileContext, ModuleAgentAnalysis
from src.providers import AgentManager
from src.providers.tools.shared_tools import search_informations
from src.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


async def analyze_modules_hierarchically(state: HierarchicalPRAnalysisState) -> Dict:
    logger.info("[NODE: hierarchical_analysis] Starting hierarchical module analysis")
    logger.info(f"[NODE: hierarchical_analysis] Total modules: {len(state['modules'])}")

    results: List[ModuleAgentAnalysis] = []

    for module_name, files in state["modules"].items():
        logger.info(f"[NODE: hierarchical_analysis] Analyzing module '{module_name}' ({len(files)} files)")

        try:
            context = _build_module_context(module_name, files)

            security_result = await _run_agent_analysis(context, "Security")
            logical_result = await _run_agent_analysis(context, "Logical")
            performance_result = await _run_agent_analysis(context, "Performance")
            clean_code_result = await _run_agent_analysis(context, "CleanCoder")

            module_analysis: ModuleAgentAnalysis = {
                "module_name": module_name,
                "files": files,
                "security_analysis": security_result,
                "logical_analysis": logical_result,
                "performance_analysis": performance_result,
                "clean_code_analysis": clean_code_result,
            }

            results.append(module_analysis)

            total_issues = (
                len(security_result.get("issues", [])) +
                len(logical_result.get("issues", [])) +
                len(performance_result.get("issues", [])) +
                len(clean_code_result.get("issues", []))
            )

            logger.info(f"[NODE: hierarchical_analysis] ✓ Module '{module_name}' complete: {total_issues} total issues")

        except Exception as e:
            logger.error(f"[NODE: hierarchical_analysis] Error analyzing module '{module_name}': {e}")
            results.append({
                "module_name": module_name,
                "files": files,
                "security_analysis": {"issues": [], "error": str(e)},
                "logical_analysis": {"issues": [], "error": str(e)},
                "performance_analysis": {"issues": [], "error": str(e)},
                "clean_code_analysis": {"issues": [], "error": str(e)},
            })

    logger.info(f"[NODE: hierarchical_analysis] ✓ All modules analyzed. Total: {len(results)} modules")
    return {"module_analyses": results}


async def _run_agent_analysis(context: str, agent_name: str) -> Dict[str, Any]:
    try:
        agent = AgentManager.get_agents(tools=[search_informations], agent_name=agent_name)
        response = await agent.ainvoke({"context": context})

        if hasattr(response, "content"):
            if isinstance(response.content, list):
                analysis_text = str(response.content)
            else:
                analysis_text = response.content
        else:
            analysis_text = str(response)

        return parse_llm_json_response(analysis_text)

    except Exception as e:
        logger.error(f"[NODE: hierarchical_analysis] Error in {agent_name} agent: {e}")
        return {"issues": [], "error": str(e)}


def _build_module_context(module_name: str, files: List[FileContext]) -> str:
    context_parts = []

    context_parts.append(f"# Módulo: {module_name}")
    context_parts.append(f"Total de arquivos modificados neste módulo: {len(files)}\n")

    for file in files:
        context_parts.append(f"\n## Arquivo: {file['path']}")
        context_parts.append(f"\n```diff\n{file['diff']}\n```")

    return "\n".join(context_parts)

import logging
from langgraph.graph import StateGraph, END

from src.core.states import HierarchicalPRAnalysisState
from src.core.nodes.grouping import group_by_module
from src.core.nodes.hierarchical_analysis import analyze_modules_hierarchically
from src.core.nodes.report_generation import generate_hierarchical_report

logger = logging.getLogger(__name__)


def create_hierarchical_pr_workflow():
    workflow = StateGraph(HierarchicalPRAnalysisState)

    workflow.add_node("group_by_module", group_by_module)
    workflow.add_node("analyze_modules", analyze_modules_hierarchically)
    workflow.add_node("generate_report", generate_hierarchical_report)

    workflow.set_entry_point("group_by_module")

    workflow.add_edge("group_by_module", "analyze_modules")
    workflow.add_edge("analyze_modules", "generate_report")
    workflow.add_edge("generate_report", END)

    app = workflow.compile()
    return app


async def run_hierarchical_pr_analysis(files: list) -> str:
    logger.info("[WORKFLOW] Starting hierarchical PR analysis")
    logger.info(f"[WORKFLOW] Total files: {len(files)}")

    app = create_hierarchical_pr_workflow()

    initial_state: HierarchicalPRAnalysisState = {
        "all_files": files,
        "modules": {},
        "module_analyses": [],
        "final_report": "",
    }

    final_state = await app.ainvoke(initial_state)

    logger.info("[WORKFLOW] ✓ Hierarchical analysis complete")
    return final_state["final_report"]

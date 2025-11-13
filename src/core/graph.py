import logging

from langgraph.graph import StateGraph, END

from src.core import PRAnalysisState
from src.core.nodes.clean_coder_agent_node import clean_coder_analysis_node
from src.core.nodes.fetch_pr_data_node import fetch_pr_data_node
from src.core.nodes.logical_agent_node import logical_analysis_node
from src.core.nodes.performance_agent_node import performance_analysis_node
from src.core.nodes.reviewer_agent_node import reviewer_analysis_node
from src.core.nodes.security_agent_node import security_analysis_node
from src.core.nodes.setup_rag_node import setup_rag_node
from src.core.nodes.cleanup_node import cleanup_resources_node
from src.core.router import should_continue_or_end

logger = logging.getLogger(__name__)

workflow = StateGraph(PRAnalysisState)

workflow.add_node("fetch_pr_data", fetch_pr_data_node)
workflow.add_node("setup_rag", setup_rag_node)
workflow.add_node("security_agent", security_analysis_node)
workflow.add_node("performance_agent", performance_analysis_node)
workflow.add_node("clean_coder_agent", clean_coder_analysis_node)
workflow.add_node("logical_agent", logical_analysis_node)
workflow.add_node("reviewer_agent", reviewer_analysis_node)
workflow.add_node("cleanup", cleanup_resources_node)

workflow.set_entry_point("fetch_pr_data")

workflow.add_conditional_edges(
    "fetch_pr_data",
    should_continue_or_end,
    {"reviewer_agent": "setup_rag", "END": END},  # 🆕 Vai para setup_rag agora!
)

workflow.add_edge("setup_rag", "security_agent")
workflow.add_edge("security_agent", "performance_agent")
workflow.add_edge("performance_agent", "clean_coder_agent")
workflow.add_edge("clean_coder_agent", "logical_agent")
workflow.add_edge("logical_agent", "reviewer_agent")
workflow.add_edge("reviewer_agent", "cleanup")
workflow.add_edge("cleanup", END)

graph = workflow.compile()

logger.info("[GRAPH] Workflow compiled successfully with RAG support and cleanup")

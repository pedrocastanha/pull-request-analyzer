import logging

from langgraph.graph import StateGraph, END

from src.core import PRAnalysisState
from src.core.nodes.reviewer_debate_node import reviewer_debate_node
from src.core.nodes.api_design_node import api_design_analyst_node
from src.core.nodes.clean_coder_agent_node import clean_coder_analysis_node
from src.core.nodes.error_handling import error_handling_analyst_node
from src.core.nodes.fetch_pr_data_node import fetch_pr_data_node
from src.core.nodes.logical_agent_node import logical_analysis_node
from src.core.nodes.performance_agent_node import performance_analysis_node
from src.core.nodes.reviewer_agent_node import reviewer_analysis_node
from src.core.nodes.security_agent_node import security_analysis_node
from src.core.nodes.setup_rag_node import setup_rag_node
from src.core.nodes.aggregate_analyses_node import aggregate_analyses_node
from src.core.nodes.publish_comments_node import publish_comments_node
from src.core.nodes.cleanup_node import cleanup_resources_node
from src.core.nodes.create_batches_node import create_batches_node
from src.core.router import (
    should_continue_or_end,
    should_review_batch_or_skip,
    should_process_next_batch_or_end,
)

logger = logging.getLogger(__name__)

workflow = StateGraph(PRAnalysisState)

workflow.add_node("fetch_pr_data", fetch_pr_data_node)
workflow.add_node("create_batches", create_batches_node)
workflow.add_node("setup_rag", setup_rag_node)
workflow.add_node("security_agent", security_analysis_node)
workflow.add_node("performance_agent", performance_analysis_node)
workflow.add_node("clean_coder_agent", clean_coder_analysis_node)
workflow.add_node("logical_agent", logical_analysis_node)
workflow.add_node("api_design_agent", api_design_analyst_node)
workflow.add_node("error_handling_agent", error_handling_analyst_node)
workflow.add_node("aggregate_analyses", aggregate_analyses_node)
workflow.add_node("reviewer_agent", reviewer_analysis_node)
workflow.add_node("reviewer_debate", reviewer_debate_node)
workflow.add_node("publish_comments", publish_comments_node)
workflow.add_node("check_next_batch", lambda state: {})
workflow.add_node("cleanup", cleanup_resources_node)

workflow.set_entry_point("fetch_pr_data")

workflow.add_conditional_edges(
    "fetch_pr_data",
    should_continue_or_end,
    {"reviewer_agent": "create_batches", "END": END},
)

workflow.add_edge("create_batches", "setup_rag")

workflow.add_edge("setup_rag", "security_agent")
workflow.add_edge("setup_rag", "performance_agent")
workflow.add_edge("setup_rag", "clean_coder_agent")
workflow.add_edge("setup_rag", "logical_agent")
workflow.add_edge("setup_rag", "api_design_agent")
workflow.add_edge("setup_rag", "error_handling_agent")

workflow.add_edge("security_agent", "aggregate_analyses")
workflow.add_edge("performance_agent", "aggregate_analyses")
workflow.add_edge("clean_coder_agent", "aggregate_analyses")
workflow.add_edge("logical_agent", "aggregate_analyses")
workflow.add_edge("api_design_agent", "aggregate_analyses")
workflow.add_edge("error_handling_agent", "aggregate_analyses")

workflow.add_conditional_edges(
    "aggregate_analyses",
    should_review_batch_or_skip,
    {"reviewer_agent": "reviewer_agent", "check_next_batch": "check_next_batch"},
)

workflow.add_edge("reviewer_agent", "reviewer_debate")
workflow.add_edge("reviewer_debate", "publish_comments")

workflow.add_conditional_edges(
    "publish_comments",
    should_process_next_batch_or_end,
    {"setup_rag": "setup_rag", "cleanup": "cleanup"},
)

workflow.add_conditional_edges(
    "check_next_batch",
    should_process_next_batch_or_end,
    {"setup_rag": "setup_rag", "cleanup": "cleanup"},
)

workflow.add_edge("cleanup", END)

graph = workflow.compile(
    checkpointer=None, interrupt_before=None, interrupt_after=None, debug=False
)
graph.config = {"recursion_limit": 500}

mermaid_code = graph.get_graph().draw_mermaid()
print(mermaid_code)

logger.info(
    "[GRAPH] Workflow compiled successfully with comment publication and cleanup"
)

import logging
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agents.separator_agent import separator_agent_node
from agents.analyzer_agent import analyzer_agent_node
from agents.commentator_agent import commentator_agent_node
from tools.tools_documentation import tools_documentation
from tools.tools_google import tools_google
from models.pr_state import PRState
from agents.supervisor_agent import supervisor_node
from nodes import final_response_node
from router import (
    conditional_router, 
    after_separator_decide, 
    after_analyzer_decide, 
    after_commentator_decide
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

logger.info("Montando o grafo de agentes...")

workflow = StateGraph(PRState)

# Adiciona os nós do grafo
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("separator_agent", separator_agent_node)
workflow.add_node("analyzer_agent", analyzer_agent_node)
workflow.add_node("commentator_agent", commentator_agent_node)

# Nós de ferramentas (apenas para analyzer)
workflow.add_node("documentation_tools", ToolNode(tools_documentation))
workflow.add_node("google_tools", ToolNode(tools_google))

# Nó final
workflow.add_node("final_response", final_response_node)

# Define o ponto de entrada
workflow.set_entry_point("supervisor")

# Arestas condicionais do supervisor
workflow.add_conditional_edges(
    "supervisor",
    conditional_router,
    {
        "separator_agent": "separator_agent",
        "analyzer_agent": "analyzer_agent",
        "commentator_agent": "commentator_agent",
        "end_analysis": "final_response",
    }
)

# Arestas condicionais do separator
workflow.add_conditional_edges(
    "separator_agent",
    after_separator_decide,
    {
        "analyzer_agent": "analyzer_agent",
        "end_analysis": "final_response",
    }
)

# Arestas condicionais do analyzer
workflow.add_conditional_edges(
    "analyzer_agent",
    after_analyzer_decide,
    {
        "use_documentation_tools": "documentation_tools",
        "use_google_tools": "google_tools",
        "separator_agent": "separator_agent",  # Pode voltar se a divisão não fizer sentido
        "commentator_agent": "commentator_agent",
        "end_analysis": "final_response",
    }
)

# Arestas condicionais do commentator
workflow.add_conditional_edges(
    "commentator_agent",
    after_commentator_decide,
    {
        "end_analysis": "final_response",
    }
)

# Arestas de retorno das ferramentas
workflow.add_edge("documentation_tools", "analyzer_agent")
workflow.add_edge("google_tools", "analyzer_agent")

# Aresta final
workflow.add_edge("final_response", END)

app = workflow.compile()

logger.info("Grafo compilado e pronto para uso.")

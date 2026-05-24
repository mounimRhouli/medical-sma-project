"""
LangGraph Graph — Medical Clinical Orientation Workflow.
Defines the StateGraph with supervisor, diagnostic_agent, physician_review,
and report_agent nodes. Compiled with MemorySaver and HITL interrupt.
"""

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from backend.app.state import MedicalState
from backend.app.nodes.supervisor import supervisor_node
from backend.app.nodes.diagnostic_agent import diagnostic_agent_node
from backend.app.nodes.physician_review import physician_review_node
from backend.app.nodes.report_agent import report_agent_node


def route_supervisor(state: MedicalState) -> str:
    """
    Fonction de routage conditionnel pour le superviseur.
    Retourne le nom du prochain nœud basé sur state['next'].
    """
    next_node = state.get("next", "diagnostic_agent")
    if next_node == "FINISH":
        return END
    return next_node


def build_graph() -> StateGraph:
    """Construit le graphe LangGraph du workflow médical."""
    graph = StateGraph(MedicalState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("diagnostic_agent", diagnostic_agent_node)
    graph.add_node("physician_review", physician_review_node)
    graph.add_node("report_agent", report_agent_node)

    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "diagnostic_agent": "diagnostic_agent",
            "physician_review": "physician_review",
            "report_agent": "report_agent",
            END: END,
        },
    )

    graph.add_edge("diagnostic_agent", "supervisor")
    graph.add_edge("physician_review", "supervisor")
    graph.add_edge("report_agent", "supervisor")

    return graph


checkpointer = MemorySaver()

medical_graph = build_graph().compile(
    checkpointer=checkpointer,
    interrupt_before=["physician_review"],
)

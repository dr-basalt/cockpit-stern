from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.nodes.filter_sp import filter_sp_node
from app.agents.nodes.supervisor import supervisor_node
from app.agents.nodes.clone import clone_node
from app.agents.nodes.anti import anti_node
from app.agents.nodes.sp_response import sp_response_node
from app.agents.nodes.formatter import formatter_node


def route_after_supervisor(state: AgentState) -> str:
    agent = state.get("active_agent", "clone")
    if agent == "real":
        return "hitl"
    return agent


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("filter_sp", filter_sp_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("clone", clone_node)
    graph.add_node("anti", anti_node)
    graph.add_node("sp", sp_response_node)
    graph.add_node("formatter", formatter_node)

    # Entry point
    graph.set_entry_point("filter_sp")

    # Edges
    graph.add_edge("filter_sp", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "clone": "clone",
            "anti": "anti",
            "sp": "sp",
            "hitl": END,  # HITL interrupts — returns to user for decision
        },
    )

    graph.add_edge("clone", "formatter")
    graph.add_edge("anti", "formatter")
    graph.add_edge("sp", "formatter")
    graph.add_edge("formatter", END)

    return graph.compile()

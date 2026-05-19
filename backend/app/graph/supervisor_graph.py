"""
Supervisor Graph: the core LangGraph orchestrator.

Replaces orchestrator/graph.py. Removes ACP/OpenClaw dependency.
All agents are called directly as Python functions — no intermediary layer.
"""
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.router import router_node

# ── Real agent imports ─────────────────────────────────────────────────────
from app.agents.sql_agent import sql_agent_node
from app.agents.general_agent import general_agent_node
from app.agents.synthesizer import synthesizer_node
from app.agents.forecast_agent import forecast_agent_node
from app.agents.contract_agent import contract_agent_node
from app.agents.risk_agent import risk_agent_node
from app.agents.delete_agent import delete_agent_node
from app.agents.email_agent import email_agent_node
from app.agents.rag_agent import rag_agent_node
from app.agents.metrics_agent import metrics_agent_node
from app.agents.data_quality_agent import data_quality_agent_node
from app.agents.mbr_summary_agent import mbr_summary_agent_node
from app.agents.forecast_variance_agent import forecast_variance_agent_node
from app.agents.revenue_recognition_agent import revenue_recognition_agent_node
from app.agents.raid_recommendation_agent import raid_recommendation_agent_node
from app.agents.contract_sow_agent import contract_sow_agent_node


# All agents are fully ported.



# ── Conditional edges ──────────────────────────────────────────────────────

def _sql_decision(state: AgentState):
    """SQL Agent either answers directly (END) or falls back to the router."""
    decision = state.get("next_node")
    if decision == "router":
        return "router"
    return "END"


def _route_decision(state: AgentState):
    """Map router decision to graph node names."""
    decision = state.get("next_node", "general_agent")
    # For "both" — fan out to forecast and contract then synthesize
    if decision == "both":
        return ["forecast_agent", "contract_agent"]
    if decision == "plan-forecast_agent":
        return ["forecast_agent"]
    return [decision]


# ── Build Graph ────────────────────────────────────────────────────────────

def build_chat_graph():
    """Build the user-chat LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Register all nodes
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("router", router_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("forecast_agent", forecast_agent_node)
    workflow.add_node("forecast_variance_agent", forecast_variance_agent_node)
    workflow.add_node("metrics_agent", metrics_agent_node)
    workflow.add_node("revenue_recognition_agent", revenue_recognition_agent_node)
    workflow.add_node("raid_recommendation_agent", raid_recommendation_agent_node)
    workflow.add_node("risk_agent", risk_agent_node)
    workflow.add_node("contract_agent", contract_agent_node)
    workflow.add_node("contract_sow_agent", contract_sow_agent_node)
    workflow.add_node("data_quality_agent", data_quality_agent_node)
    workflow.add_node("mbr_summary_agent", mbr_summary_agent_node)
    workflow.add_node("delete_agent", delete_agent_node)
    workflow.add_node("email_agent", email_agent_node)
    workflow.add_node("general_agent", general_agent_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # Entry: all queries hit SQL Agent first
    workflow.set_entry_point("sql_agent")

    # SQL Agent → END or → Router
    workflow.add_conditional_edges(
        "sql_agent",
        _sql_decision,
        {
            "router": "router",
            "END": END,
        },
    )

    # Router → specialist agents
    workflow.add_conditional_edges(
        "router",
        _route_decision,
        {
            "forecast_agent": "forecast_agent",
            "contract_agent": "contract_agent",
            "rag_agent": "rag_agent",
            "forecast_variance_agent": "forecast_variance_agent",
            "metrics_agent": "metrics_agent",
            "revenue_recognition_agent": "revenue_recognition_agent",
            "raid_recommendation_agent": "raid_recommendation_agent",
            "risk_agent": "risk_agent",
            "contract_sow_agent": "contract_sow_agent",
            "data_quality_agent": "data_quality_agent",
            "mbr_summary_agent": "mbr_summary_agent",
            "delete_agent": "delete_agent",
            "email_agent": "email_agent",
            "general_agent": "general_agent",
        },
    )

    # Forecast + Contract → Synthesizer (for "both" route)
    workflow.add_edge("forecast_agent", "synthesizer")
    workflow.add_edge("contract_agent", "synthesizer")
    workflow.add_edge("synthesizer", END)

    # All other specialist agents → END directly
    for agent in [
        "rag_agent", "forecast_variance_agent", "metrics_agent",
        "revenue_recognition_agent", "raid_recommendation_agent",
        "risk_agent", "contract_sow_agent", "data_quality_agent",
        "mbr_summary_agent", "delete_agent", "email_agent", "general_agent",
    ]:
        workflow.add_edge(agent, END)

    return workflow.compile()


# Singleton graph instance
chat_graph = build_chat_graph()

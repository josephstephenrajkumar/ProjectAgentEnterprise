"""
Supervisor Graph: the core LangGraph orchestrator.

Replaces orchestrator/graph.py. Removes ACP/OpenClaw dependency.

Fixed Python nodes (infrastructure / complex logic):
  - sql_agent, router, synthesizer, general_agent, delete_agent, risk_agent

Configurable agents (loaded from AgentConfig table via GenericAgentRunner):
  - forecast_variance_agent, metrics_agent, revenue_recognition_agent,
    raid_recommendation_agent, contract_sow_agent, data_quality_agent,
    mbr_summary_agent, email_agent, forecast_agent, contract_agent, rag_agent

To add a new agent: INSERT a row into AgentConfig + TriggerKeyword — no code needed.
"""
from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.router import router_node

# ── Fixed infrastructure nodes (Python) ───────────────────────────────────
from app.agents.sql_agent import sql_agent_node
from app.agents.general_agent import general_agent_node
from app.agents.synthesizer import synthesizer_node
from app.agents.delete_agent import delete_agent_node
from app.agents.risk_agent import risk_agent_node

# ── Generic runner: powers all configurable specialist agents ──────────────
from app.agents.generic_agent_runner import make_agent_node, load_all_active_agent_ids


# ── Fixed infrastructure nodes that are not configurable ──────────────────
# These remain as Python nodes because they have complex specialised logic:
#   sql_agent:    dynamic SQL generation, schema layer, memory scoring
#   router:       three-layer hybrid intent routing
#   synthesizer:  fan-in report merging for 'both' route
#   general_agent: free-form LLM conversation fallback
#   delete_agent: destructive operation — never configurable
#   risk_agent:   high-complexity multi-stage RAID analysis

FIXED_NODES = {
    "sql_agent":     sql_agent_node,
    "router":        router_node,
    "synthesizer":   synthesizer_node,
    "general_agent": general_agent_node,
    "delete_agent":  delete_agent_node,
    "risk_agent":    risk_agent_node,
}

# Configurable agents that route through synthesizer for 'both' path
BOTH_ROUTE_AGENTS = ["forecast_variance_agent", "contract_sow_agent"]


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
    if decision == "both":
        return ["forecast_variance_agent", "contract_sow_agent"]
    return [decision]


# ── Build Graph ────────────────────────────────────────────────────────────

def build_chat_graph():
    """Build the user-chat LangGraph workflow.

    Fixed nodes are registered from Python imports.
    Configurable agents are loaded dynamically from the AgentConfig table
    and registered via make_agent_node() factory — no hardcoded imports needed.
    """
    workflow = StateGraph(AgentState)

    # Register fixed infrastructure nodes
    for node_id, node_fn in FIXED_NODES.items():
        workflow.add_node(node_id, node_fn)

    # Dynamically register all active configurable agents from AgentConfig
    configurable_agent_ids = load_all_active_agent_ids()
    registered_configurable = []
    for agent_id in configurable_agent_ids:
        if agent_id not in FIXED_NODES:
            workflow.add_node(agent_id, make_agent_node(agent_id))
            registered_configurable.append(agent_id)

    # Build the full set of routable agent IDs for conditional edges
    all_routable = list(FIXED_NODES.keys()) + registered_configurable
    # Remove non-routable infrastructure nodes
    non_routable = {"sql_agent", "router", "synthesizer"}
    routable_agents = [a for a in all_routable if a not in non_routable]

    # Entry: all queries hit SQL Agent first
    workflow.set_entry_point("sql_agent")

    # SQL Agent → END or → Router
    workflow.add_conditional_edges(
        "sql_agent",
        _sql_decision,
        {"router": "router", "END": END},
    )

    # Router → specialist agents (dynamic map built from registered nodes)
    route_map = {agent_id: agent_id for agent_id in routable_agents}
    workflow.add_conditional_edges("router", _route_decision, route_map)

    # 'both' fan-out: forecast + contract → synthesizer → END
    for both_agent in BOTH_ROUTE_AGENTS:
        if both_agent in (registered_configurable + list(FIXED_NODES.keys())):
            workflow.add_edge(both_agent, "synthesizer")
    workflow.add_edge("synthesizer", END)

    # All other specialist agents → END directly
    direct_to_end = [
        a for a in routable_agents
        if a not in BOTH_ROUTE_AGENTS and a != "synthesizer"
    ]
    for agent_id in direct_to_end:
        workflow.add_edge(agent_id, END)

    return workflow.compile()


# Singleton graph instance
chat_graph = build_chat_graph()

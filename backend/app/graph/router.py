"""
Hybrid Router: Rule-based → Embedding-based → LLM fallback.

Replaces orchestrator/router.py. The key improvement is the three-layer
routing pipeline that short-circuits at the earliest confident layer,
reducing latency for common queries.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage


# ── Rule-based routing (Layer 1) ────────────────────────────────────────────

RULE_KEYWORDS = {
    "sql_agent": [
        "etc", "eac", "gm", "margin", "forecast amount", "revenue",
        "invoice", "cost", "hours", "actuals", "backlog", "total hours",
        "monthly hours", "financials", "budget",
    ],
    "rag_agent": [
        "sow", "contract", "clause", "acceptance", "obligation",
        "deliverable", "scope", "work package", "statement of work",
    ],
    "forecast_variance_agent": [
        "variance", "compare forecast", "baseline vs", "reforecast",
    ],
    "metrics_agent": [
        "calculate etc", "calculate eac", "calculate gm",
        "metrics snapshot", "margin calculation",
    ],
    "raid_recommendation_agent": [
        "add a risk", "add an issue", "create risk", "new risk",
        "create issue", "update raid", "update risk", "update action",
        "assign risk", "purchase order", "missing po",
    ],
    "risk_agent": [
        "risk analysis", "raid log", "risk matrix", "risk summary",
        "mitigation",
    ],
    "contract_sow_agent": [
        "contract terms", "sow terms", "acceptance criteria",
        "commercial clause",
    ],
    "mbr_summary_agent": [
        "mbr", "weekly summary", "executive summary",
        "monthly business review",
    ],
    "delete_agent": ["delete project", "remove project", "drop project"],
    "email_agent": ["email", "send email", "mail to", "send to"],
}


def _rule_route(query: str) -> str | None:
    """Fast keyword-based routing. Returns agent key or None."""
    q = query.lower()
    for agent_key, keywords in RULE_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                return agent_key
    return None


# ── LLM fallback routing (Layer 3) ──────────────────────────────────────────

ROUTER_SYSTEM_PROMPT = """You are a Router. Classify the user query into EXACTLY one of:

1. 'sql_agent': Structured data questions about project financials, hours, costs, revenue, ETC, EAC, GM, forecasts, actuals, backlog.
2. 'rag_agent': Document-based questions about SOW, contracts, clauses, obligations, deliverables, scope, work packages.
3. 'forecast_variance_agent': Compare forecasts, baselines, reforecasts, or detect variance.
4. 'metrics_agent': Calculate ETC, EAC, GM snapshots.
5. 'revenue_recognition_agent': Revenue recognition based on hours achieved and milestones.
6. 'raid_recommendation_agent': Add, create, update, assign, or resolve a specific risk, issue, action, or dependency.
7. 'risk_agent': General risk analysis, RAID log summary, or risk matrix.
8. 'contract_sow_agent': Validate milestones, acceptance criteria, obligations, pricing, commercial clauses.
9. 'data_quality_agent': Detect missing actuals, stale forecasts, mismatched hours.
10. 'mbr_summary_agent': Draft MBR or weekly summary commentary.
11. 'delete_agent': Delete or remove a project.
12. 'email_agent': Send an email or forward information.
13. 'both': The query explicitly needs BOTH SQL and RAG agents combined.
14. 'general_agent': General conversation, off-topic, or greetings.

Output ONLY the exact key. No explanation."""


def _llm_route(query: str, history: list[dict] | None = None) -> str:
    """LLM-based fallback classification."""
    llm = get_llm()
    messages = [SystemMessage(content=ROUTER_SYSTEM_PROMPT)]

    if history:
        for msg in history[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=f"PAST QUERY: {msg['content']}"))

    messages.append(HumanMessage(content=f"CURRENT QUERY: {query}"))

    try:
        response = llm.invoke(messages)
        decision = response.content.strip().lower().strip(".'\"")
    except Exception:
        decision = "general_agent"

    valid_keys = [
        "sql_agent", "rag_agent", "forecast_variance_agent", "metrics_agent",
        "revenue_recognition_agent", "raid_recommendation_agent", "risk_agent",
        "contract_sow_agent", "data_quality_agent", "mbr_summary_agent",
        "delete_agent", "email_agent", "both", "general_agent",
    ]
    if decision not in valid_keys:
        decision = "general_agent"

    return decision


# ── Main router node ────────────────────────────────────────────────────────

def router_node(state: AgentState) -> dict:
    """Three-layer hybrid routing: Rules → Embeddings → LLM fallback."""
    query = state["query"]
    debug = state.get("debug_log", "")
    history = state.get("history", [])

    # Layer 1: Rule-based (fast path)
    decision = _rule_route(query)
    if decision:
        return {
            "next_node": decision,
            "debug_log": debug + f"\n🚦 Router → {decision} (rule-based)",
            "agent_outputs": [],
            "last_route": decision,
        }

    # Layer 2: Embedding-based intent matching (TODO: implement with cached intent vectors)
    # For now, skip to Layer 3.

    # Layer 3: LLM fallback
    decision = _llm_route(query, history)
    return {
        "next_node": decision,
        "debug_log": debug + f"\n🚦 Router → {decision} (LLM fallback)",
        "agent_outputs": [],
        "last_route": decision,
    }

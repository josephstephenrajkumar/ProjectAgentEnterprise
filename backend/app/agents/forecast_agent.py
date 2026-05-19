"""
Plan-Forecast Agent — RAG-based agent for project estimations and forecasts.
Ported from agents/forecast_agent.py.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.rag.retrieval import similarity_search, list_collections
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


AGENT_NAME = "Plan & Forecast Agent"
PERSONA = (
    "Delivery Manager – expert in forecasts. "
    "CRITICAL: You must prioritize the 'Context' provided below over any past conversation history."
)


def _extract_project_code(query: str, history: list) -> str:
    """Ask LLM to extract a project code from the query/history."""
    llm = get_llm()
    prompt = "Extract the Project Code (e.g. BOSTON-001) from the query or history if present. Return ONLY the code, or NONE."
    try:
        combined = query + " ".join([m.get("content", "") for m in history])
        res = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=combined)])
        val = res.content.strip()
        return "" if val == "NONE" else val
    except Exception:
        return ""


def forecast_agent_node(state: AgentState) -> dict:
    query = state["query"]
    history = state.get("history", [])
    current_outputs = state.get("agent_outputs", [])
    debug = state.get("debug_log", "")
    llm = get_llm()

    target_project = _extract_project_code(query, history)
    where_filter = {"project_code": target_project} if target_project else None

    context = ""

    if target_project:
        debug += f"\n🔍 {AGENT_NAME}: Filtering RAG for project '{target_project}'"
        safe_code = target_project.replace(" ", "_").replace("-", "_").lower()
        target_collection = f"{safe_code}_estimation_milestone_collection"
        context = similarity_search(target_collection, query, k=5, where=where_filter)
    else:
        all_cols = list_collections()
        target_cols = [c for c in all_cols if "estimation_milestone_collection" in c]
        for c in target_cols:
            c_ctx = similarity_search(c, query, k=2)
            if c_ctx:
                context += f"\n--- From {c} ---\n{c_ctx}"

    if not context.strip():
        msg = f"❌ {AGENT_NAME}: No relevant estimation context found. Please specify a Project Code."
        return {
            "agent_outputs": current_outputs + [msg],
            "debug_log": debug + f"\n❌ {AGENT_NAME}: no context found.",
        }

    system_prompt = (
        f"You are the {PERSONA}.\n"
        "Answer the user query using ONLY the Context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}"
    )

    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))
    response = llm.invoke(messages)

    report_source = f" (Filtered to {target_project})" if target_project else " (Across all estimations)"
    report = f"--- 📊 {AGENT_NAME} Report{report_source} ---\n{response.content}\n"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: answered using RAG metadata filtering.",
    }

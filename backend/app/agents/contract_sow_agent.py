"""
Contract/SOW Agent.
Validates milestones, acceptance criteria, obligations against the SOW.
Uses LlamaIndex instead of raw ChromaDB.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.rag.llamaindex_service import query_collection
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "Contract/SOW Agent"

def contract_sow_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    history = state.get("history", [])
    llm = get_llm()
    
    prompt = "Extract Project Number from query. Return NONE if not found."
    identifier = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=query)]).content.strip()
    
    context = ""
    if identifier and identifier != "NONE":
        safe_code = identifier.replace(" ", "_").replace("-", "_").lower()
        col = f"{safe_code}_contract_collection"
        context = query_collection(col, query, top_k=5)
    else:
        # Fallback to global docs
        context = query_collection("global_docs_collection", query, top_k=5)
        
    if not context.strip():
        return {
            "agent_outputs": current_outputs + [f"❌ {AGENT_NAME}: Could not find relevant SOW/Contract text."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No context found.",
        }

    sys_prompt = f"You are a Contract Validation Expert. Use the following context to answer questions about SOWs, milestones, and commercial clauses.\n\nContext:\n{context}"
    
    messages = [SystemMessage(content=sys_prompt)]
    for msg in history[-4:]:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
    messages.append(HumanMessage(content=query))
    
    response = llm.invoke(messages)
    report = f"--- 📜 {AGENT_NAME} Report ---\n{response.content.strip()}"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated contract validation report.",
    }

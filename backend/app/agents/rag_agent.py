"""
General RAG Agent.
A fallback agent that searches across all embedded documents using LlamaIndex.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.rag.llamaindex_service import query_collection
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "General RAG Agent"

def rag_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    history = state.get("history", [])
    llm = get_llm()
    
    # Check if we have specific collections to search from the state
    collections_to_search = state.get("collection_names")
    
    context = ""
    if collections_to_search:
        debug += f"\n🔍 {AGENT_NAME}: Searching specific collections: {collections_to_search}"
        for col in collections_to_search:
            col_ctx = query_collection(col, query, top_k=3)
            if col_ctx:
                context += f"\n--- From {col} ---\n{col_ctx}"
    else:
        debug += f"\n🔍 {AGENT_NAME}: No specific collections provided. Attempting generic search..."
        # In a real implementation, we would either search a "global" index or ask the router.
        # For now, we simulate a global search query to a default collection.
        context = query_collection("global_docs_collection", query, top_k=5)

    if not context.strip():
        msg = f"❌ {AGENT_NAME}: I couldn't find any relevant documents to answer your question."
        return {
            "agent_outputs": current_outputs + [msg],
            "debug_log": debug + f"\n❌ {AGENT_NAME}: No context found.",
        }

    system_prompt = (
        f"You are a helpful knowledge assistant.\n"
        "Answer the user query using ONLY the Context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{context}"
    )

    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            # Simple assumption that history contains generic dictionaries
            messages.append(SystemMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))
    
    try:
        response = llm.invoke(messages)
        report = f"--- 📚 {AGENT_NAME} Report ---\n{response.content.strip()}"
    except Exception as e:
        report = f"❌ {AGENT_NAME} encountered an error: {e}"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated response from documents.",
    }

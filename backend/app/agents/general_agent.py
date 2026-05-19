"""
General Agent — handles greetings, off-topic, and general conversation.
Ported from agents/general_agent.py.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


SYSTEM_PROMPT = (
    "You are a friendly and knowledgeable assistant for ProjectAgentEnterprise. "
    "Answer the user's question helpfully and concisely."
)


def general_agent_node(state: AgentState) -> dict:
    query = state["query"]
    history = state.get("history", [])
    debug = state.get("debug_log", "")
    llm = get_llm()

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))
    response = llm.invoke(messages)

    return {
        "response": response.content,
        "debug_log": debug + "\n💬 General Agent: free-form response.",
    }

"""
Synthesizer Agent — merges outputs from multiple specialist agents.
Ported from agents/synthesizer.py.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


SUPERVISOR_PROMPT = """You are a Project Manager Supervisor.
Synthesise the following specialist reports into a single, clear, and
structured answer for the client. Highlight any discrepancies between
reports if present. Do not invent information not found in the reports.

Team Reports:
{reports}"""


def synthesizer_node(state: AgentState) -> dict:
    outputs = state.get("agent_outputs", [])
    debug = state.get("debug_log", "")
    query = state["query"]
    llm = get_llm()

    if not outputs:
        return {
            "response": "I could not retrieve information from the agents.",
            "debug_log": debug + "\n⚠️ Synthesizer: no agent outputs to merge.",
        }

    combined = "\n".join(outputs)
    prompt = SUPERVISOR_PROMPT.format(reports=combined)

    history = state.get("history", [])
    messages = [SystemMessage(content=prompt)]
    for msg in history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))
    response = llm.invoke(messages)

    return {
        "response": response.content,
        "debug_log": debug + "\n🤖 Synthesizer: merged outputs.",
    }

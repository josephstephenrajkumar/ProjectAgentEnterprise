"""
RAID Recommendation Agent.
Suggests new risks, issues, or mitigating actions to add to the RAID log.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.raid_service import get_raid_items
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "RAID Recommendation Agent"

def raid_recommendation_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    llm = get_llm()
    
    prompt = "Extract Project Number from query. Return NONE if not found."
    identifier = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=query)]).content.strip()
    
    if identifier == "NONE" or not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to suggest RAID items for."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }

    debug += f"\n🔍 {AGENT_NAME}: Fetching existing RAID items to find gaps for project '{identifier}'"
    raid_items = get_raid_items(identifier)
    
    sys_prompt = "You are a proactive Delivery Manager. Suggest 2 potential risks that might be missing from this project's RAID log, or suggest improved mitigations for existing risks. Current RAID items:"
    hist_prompt = f"{raid_items}\nUser asks: {query}"
    
    response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=hist_prompt)])
    
    report = f"--- 🛡️ {AGENT_NAME} Report ---\n{response.content.strip()}"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated RAID recommendations.",
    }

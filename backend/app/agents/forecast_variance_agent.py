"""
Forecast Variance Agent.
Compares a project's forecasts (current vs baseline/previous) to detect variance.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.forecast_version_service import get_plan_versions
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "Forecast Variance Agent"

def forecast_variance_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    
    # Simple mock for extracting ID. Real implementation would be robust.
    # We will assume a hardcoded or basic extraction logic.
    llm = get_llm()
    prompt = "Extract Project Number from query. Return NONE if not found."
    identifier = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=query)]).content.strip()
    
    if identifier == "NONE" or not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to run a variance report on."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }

    debug += f"\n🔍 {AGENT_NAME}: Fetching plan versions for project '{identifier}'"
    versions = get_plan_versions(identifier)
    
    if len(versions) < 2:
        return {
            "agent_outputs": current_outputs + [f"⚠️ Project '{identifier}' has fewer than two forecast versions. Cannot calculate variance."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: Not enough versions for variance.",
        }

    # Simulate variance calculation and LLM drafting
    sys_prompt = "You are a financial analyst. Draft a brief variance report given these two latest versions."
    hist_prompt = f"Latest version: {versions[0]}\nPrevious version: {versions[1]}"
    response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=hist_prompt)])
    
    report = f"--- 📉 {AGENT_NAME} Report ---\n{response.content.strip()}"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated variance report.",
    }

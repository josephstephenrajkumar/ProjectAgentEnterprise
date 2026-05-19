"""
Revenue Recognition Agent.
An agent that explains or calculates revenue recognition for a project.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.revenue_recognition_service import recognize_revenue
from app.services.forecast_version_service import get_current_plan_version
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "Revenue Recognition Agent"

def revenue_recognition_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    llm = get_llm()
    
    prompt = "Extract Project Number from query. Return NONE if not found."
    identifier = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=query)]).content.strip()
    
    if identifier == "NONE" or not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to check revenue recognition."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }

    debug += f"\n🔍 {AGENT_NAME}: Checking rev rec for project '{identifier}'"
    
    # Needs actual implementation to map to project ID and reporting month
    # Here is a mock implementation utilizing the service
    current_plan = get_current_plan_version(identifier)
    plan_id = current_plan['plan_version_id'] if current_plan else "mock-plan-id"
    
    recognized = recognize_revenue(identifier, plan_id, "2026-04-01")
    
    report = f"--- 💸 {AGENT_NAME} Report ---\n"
    report += f"**Revenue Recognition for {identifier}**:\n"
    report += f"Calculated Revenue to Recognize (Current Period): **${recognized:,.2f}**\n\n"
    report += "> Note: This is an estimated calculation based on current actuals and milestone completion."

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated rev rec report.",
    }

"""
Metrics Agent.
An agent that uses the Metrics Service to calculate and return ETC, EAC, and GM metrics.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.metrics_service import get_latest_metrics
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "Metrics Agent"

EXTRACTION_PROMPT = """You are an AI assistant that extracts project identifiers (Project Number or Opportunity ID).
Analyze the user query. Return ONLY the raw identifier string (e.g., '202021').
If no identifier is found, return: NONE"""


def _extract_identifier(query: str) -> str:
    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=EXTRACTION_PROMPT),
            HumanMessage(content=query),
        ])
        result = response.content.strip()
        return "" if result == "NONE" or not result else result
    except Exception:
        return ""


def metrics_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    
    identifier = _extract_identifier(query)
    
    if not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to calculate metrics for."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }
        
    debug += f"\n🔍 {AGENT_NAME}: Fetching metrics for project '{identifier}'"
    
    metrics = get_latest_metrics(identifier) # In a real implementation, would need to map identifier -> project_id first
    
    if not metrics:
         return {
            "agent_outputs": current_outputs + [f"❌ Could not find recent metrics snapshots for '{identifier}'."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No metrics found.",
        }

    # Format the metrics report
    report = f"--- 📈 {AGENT_NAME} Report ---\n"
    report += f"**Latest Financial Snapshot for {identifier}** (As of {metrics.get('reporting_month', 'Unknown')}):\n\n"
    report += f"- **ITD Cost (Actuals):** ${metrics.get('itd_cost', 0):,.2f}\n"
    report += f"- **ITD Revenue:** ${metrics.get('itd_revenue', 0):,.2f}\n"
    report += f"- **ETC Cost (Forecast):** ${metrics.get('etc_cost', 0):,.2f}\n"
    report += f"- **EAC Cost (Total Estimate):** ${metrics.get('eac_cost', 0):,.2f}\n"
    report += f"- **EAC Revenue:** ${metrics.get('eac_revenue', 0):,.2f}\n"
    report += f"- **Gross Margin:** ${metrics.get('gm_amount', 0):,.2f} ({metrics.get('gm_percent', 0):.1f}%)\n"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated metrics report.",
    }

"""
Data Quality Agent.
An agent that uses the Data Quality Service to detect anomalies like missing actuals or stale forecasts.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.data_quality_service import run_data_quality_checks
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "Data Quality Agent"

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


def data_quality_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    
    identifier = _extract_identifier(query)
    
    if not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to run Data Quality checks for."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }
        
    debug += f"\n🔍 {AGENT_NAME}: Running DQ checks for project '{identifier}'"
    
    # In a real implementation, would need to map identifier -> project_id first
    anomalies = run_data_quality_checks(identifier) 
    
    if not anomalies:
         return {
            "agent_outputs": current_outputs + [f"✅ Data Quality Checks passed for '{identifier}'. No anomalies detected."],
            "debug_log": debug + f"\n✅ {AGENT_NAME}: Zero anomalies found.",
        }

    # Format the report
    report = f"--- 🚨 {AGENT_NAME} Report ---\n"
    report += f"**Data Anomalies Detected for {identifier}:**\n\n"
    
    for idx, a in enumerate(anomalies):
        icon = "🔴" if a.get("severity") == "HIGH" else "🟡" if a.get("severity") == "MEDIUM" else "🟢"
        report += f"{idx+1}. {icon} **[{a.get('type')}]**: {a.get('message')}\n"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated DQ report.",
    }

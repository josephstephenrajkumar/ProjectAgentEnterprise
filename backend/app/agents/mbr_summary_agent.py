"""
MBR Summary Agent.
Drafts Weekly Status Reports or Monthly Business Review (MBR) commentary.
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.services.summary_service import get_weekly_summaries, get_mbr_items
from langchain_core.messages import SystemMessage, HumanMessage


AGENT_NAME = "MBR Summary Agent"

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


def mbr_summary_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    current_outputs = state.get("agent_outputs", [])
    llm = get_llm()
    
    identifier = _extract_identifier(query)
    
    if not identifier:
        return {
            "agent_outputs": current_outputs + ["❌ Please provide a Project Number to generate a summary for."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No identifier found.",
        }
        
    debug += f"\n🔍 {AGENT_NAME}: Fetching summary data for project '{identifier}'"
    
    # In a real implementation, would need to map identifier -> project_id first
    summaries = get_weekly_summaries(identifier, limit=2)
    mbr_items = get_mbr_items(identifier)
    
    if not summaries and not mbr_items:
         return {
            "agent_outputs": current_outputs + [f"❌ Could not find recent status reports or MBR data for '{identifier}'."],
            "debug_log": debug + f"\n⚠️ {AGENT_NAME}: No summary data found.",
        }

    # Ask the LLM to draft a new summary based on recent history
    draft_prompt = f"""You are a Senior Delivery Executive. Draft a concise Monthly Business Review (MBR) / Status summary based on the following historical records for project {identifier}.

    Recent Weekly Summaries:
    {summaries}

    MBR Items:
    {mbr_items}

    User Request: {query}
    """
    
    try:
        response = llm.invoke([HumanMessage(content=draft_prompt)])
        report = f"--- 📝 {AGENT_NAME} Report ---\n{response.content.strip()}"
    except Exception as e:
        report = f"❌ Failed to generate MBR Summary: {e}"

    return {
        "agent_outputs": current_outputs + [report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: generated summary report.",
    }

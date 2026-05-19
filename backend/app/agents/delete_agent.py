"""
Delete Project Agent — permanently removes a project and cascaded data.
Ported from agents/delete_project_agent.py.
"""
import sqlite3
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.config.settings import get_settings
from langchain_core.messages import SystemMessage, HumanMessage

settings = get_settings()

DELETE_EXTRACTION_PROMPT = """You are an AI assistant that extracts project identifiers from text.
The user wants to delete a project.
Extract either the Project Number (e.g., 202021) or Opportunity ID (e.g., O-1932849).
Return ONLY the raw identifier string. If not found, return: NONE"""


def _extract_identifier(query: str) -> str:
    llm = get_llm()
    try:
        response = llm.invoke([
            SystemMessage(content=DELETE_EXTRACTION_PROMPT),
            HumanMessage(content=query),
        ])
        result = response.content.strip()
        return "" if result == "NONE" or not result else result
    except Exception:
        return ""


def delete_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")

    identifier = _extract_identifier(query)
    if not identifier:
        return {
            "response": "Could not identify a Project Number or Opportunity ID to delete.",
            "debug_log": debug + "\n⚠️ Delete Agent: No identifier found.",
        }

    debug += f"\n🔍 Delete Agent: Extracted identifier '{identifier}'"

    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute(
            "SELECT project_id FROM Project WHERE ProjectNumber = ? OR OpportunityID = ?",
            (identifier, identifier),
        )
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return {
                "response": f"❌ No project found matching '{identifier}'.",
                "debug_log": debug + f"\n⚠️ Delete Agent: No project found.",
            }

        deleted_count = 0
        for row in rows:
            cursor.execute("DELETE FROM Project WHERE project_id = ?", (row[0],))
            deleted_count += 1

        conn.commit()
        conn.close()

        return {
            "response": f"✅ Successfully deleted project '{identifier}' and all associated data.",
            "debug_log": debug + f"\n✅ Delete Agent: Deleted {deleted_count} project(s).",
        }
    except Exception as exc:
        return {
            "response": f"❌ Error deleting project: {exc}",
            "debug_log": debug + f"\n❌ Delete Agent error: {exc}",
        }

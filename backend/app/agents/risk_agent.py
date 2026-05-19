"""
Risk Agent — structured risk analysis from DB + RAG fallback.
Ported from agents/risk_agent.py.
"""
import sqlite3
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.rag.retrieval import similarity_search
from app.config.settings import get_settings
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

settings = get_settings()
AGENT_NAME = "Risk Agent"

EXTRACTION_PROMPT = """You are an AI assistant that extracts project identifiers (Project Number, Opportunity ID, or SOW ID).
Analyze the conversation history and the current user query.
1. If the current query contains an identifier (e.g., '202021'), return it.
2. If the current query does NOT have an identifier, look at the RECENT conversation history for the most recently discussed project code.
3. Return ONLY the raw identifier string (e.g., '202021').
4. No extra text, markdown, or punctuation.
5. If no identifier is found in query or context, return: NONE"""


def _extract_identifier(query: str, history: list = None) -> str:
    llm = get_llm()
    try:
        messages = [SystemMessage(content=EXTRACTION_PROMPT)]
        if history:
            for msg in history[-4:]:
                role = msg.get("role")
                content = msg.get("content")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=f"Current Query: {query}"))
        response = llm.invoke(messages)
        result = response.content.strip()
        if result == "NONE" or not result:
            return ""
        return result
    except Exception:
        return ""


def _build_db_markdown(project: dict, wps: list, raids: list, identifier: str, query: str = "") -> str:
    project_number = project.get("ProjectNumber", identifier)
    query_lower = query.lower()

    only_high = "high" in query_lower and "summary" not in query_lower
    only_med = "medium" in query_lower
    only_low = "low" in query_lower
    has_specific_request = only_high or only_med or only_low

    baseline_risk_count = len(wps)
    live_risk_count = sum(1 for r in raids if str(r.get("Type", "")).lower() == "risk")
    issue_count = sum(1 for r in raids if str(r.get("Type", "")).lower() == "issue")
    total_items = baseline_risk_count + len(raids)

    high_raids = [r for r in raids if str(r.get("Status", "")).lower() in ["open", "critical", "high"]]
    med_raids = [r for r in raids if str(r.get("Status", "")).lower() not in ["open", "critical", "high", "closed", "resolved", "low"]]
    low_raids = [r for r in raids if str(r.get("Status", "")).lower() in ["closed", "resolved", "low"]]

    md = f"# ⚠️ Risk Analysis: {project_number}\n\n"

    if not has_specific_request:
        md += "## 🎯 Risk Assessment Summary\n"
        if total_items == 0:
            md += "No baseline risks or operational RAID items recorded.\n\n"
        else:
            md += f"Operational: **{live_risk_count} live risks**, **{issue_count} live issues**. "
            md += f"SOW Baseline: **{baseline_risk_count} risks** identified.\n\n"

    md += "## 📋 Operational RAID Items\n"

    def _raid_table(raid_list):
        if not raid_list:
            return ""
        tbl = "| Category | Description | Owner | Due Date | Status | Mitigation |\n"
        tbl += "|----------|-------------|-------|----------|--------|------------|\n"
        for r in raid_list:
            cat = r.get("Category") or r.get("Type") or "General"
            desc = (r.get("Description") or "").replace("\n", " ").strip()
            owner = r.get("owner", "Unassigned")
            due_date = r.get("DueDate", "No Date")
            mit_action = r.get("MitigatingAction") or r.get("ROAM") or "No mitigation stated"
            tbl += f"| {cat} | {desc} | {owner} | {due_date} | {r.get('Status', 'Unknown')} | {mit_action} |\n"
        return tbl

    if not has_specific_request or only_high:
        h_table = _raid_table(high_raids)
        if h_table:
            md += f"### 🔴 High Priority\n{h_table}\n"
    if not has_specific_request or only_med:
        m_table = _raid_table(med_raids)
        if m_table:
            md += f"### 🟡 Medium Priority\n{m_table}\n"
    if not has_specific_request or only_low:
        l_table = _raid_table(low_raids)
        if l_table:
            md += f"### 🟢 Low / Resolved Items\n{l_table}\n"

    if not has_specific_request:
        md += "## 🛡️ SOW Baseline Risks (Phase-Specific)\n"
        if wps:
            for idx, wp in enumerate(wps):
                phase = wp.get("phase_name", f"Phase {idx+1}")
                r_and_m = wp.get("risks_mitigations", "None documented")
                if r_and_m and r_and_m.lower() != "none":
                    md += f"{idx+1}. **[{phase}]**: {r_and_m}\n"
        else:
            md += "- No baseline risks found.\n"
        md += "\n"

    md += f"---\n*Retrieved for project: {project_number}*"
    return md


def risk_agent_node(state: AgentState) -> dict:
    query = state.get("query", "")
    debug = state.get("debug_log", "")
    history = state.get("history", [])
    llm = get_llm()

    identifier = _extract_identifier(query, history)

    if not identifier:
        debug += "\n⚠️ Risk Agent: Could not find a clear Project or SOW ID."
        identifier = "Unknown Document"
    else:
        debug += f"\n🔍 Risk Agent: Extracted target ID '{identifier}'"

        try:
            conn = sqlite3.connect(settings.db_abs_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM Project WHERE ProjectNumber = ? OR OpportunityID = ?", (identifier, identifier))
            proj_row = cursor.fetchone()

            if proj_row:
                proj_id = proj_row["project_id"]
                cursor.execute("SELECT phase_name, risks_mitigations FROM ProjectWorkPackage WHERE project_id = ?", (proj_id,))
                wp_rows = [dict(r) for r in cursor.fetchall()]

                raid_rows = []
                try:
                    cursor.execute("SELECT * FROM RAIDitems WHERE project_id = ?", (proj_id,))
                    raid_rows = [dict(r) for r in cursor.fetchall()]
                except sqlite3.OperationalError:
                    debug += "\n⚠️ Risk Agent: RAIDitems table not found."

                conn.close()
                debug += "\n✅ Risk Agent: Project found. Compiling structured risk report."
                md_text = _build_db_markdown(dict(proj_row), wp_rows, raid_rows, identifier, query)
                return {"response": md_text, "debug_log": debug}
            else:
                conn.close()
        except Exception as exc:
            debug += f"\n⚠️ Risk Agent DB error: {exc}"

    # RAG fallback
    debug += f"\n⚠️ Risk Agent: '{identifier}' not found in DB. Falling back to RAG."
    try:
        context_str = similarity_search("contract_collection", query, k=4)
        if not context_str:
            return {
                "response": f"I couldn't find risk information for {identifier}.",
                "debug_log": debug + "\n❌ Risk Agent: No context found.",
            }

        rag_prompt = (
            f"You are an expert contract analyst. Extract and analyze risk-related information.\n"
            f"Document Text: {context_str}\nExtract risk analysis for: {identifier}"
        )
        response = llm.invoke([HumanMessage(content=rag_prompt)])
        return {"response": response.content.strip(), "debug_log": debug}
    except Exception as exc:
        return {
            "response": f"❌ An error occurred: {exc}",
            "debug_log": debug + f"\n❌ Risk Agent RAG error: {exc}",
        }

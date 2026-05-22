"""
Generic Agent Runner — The single Python implementation that replaces
individual specialist agent files.

Instead of 14 separate Python files each duplicating the same pattern of:
  1. Extract project identifier
  2. Call a service
  3. Call LLM for synthesis
  4. Return outputs

This module loads agent configuration from the AgentConfig database table
and assembles an execution plan dynamically from the registered tool library.

Usage in supervisor_graph.py:
    from app.agents.generic_agent_runner import make_agent_node
    workflow.add_node("mbr_summary_agent", make_agent_node("mbr_summary_agent"))
"""

import json
import sqlite3
import uuid
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.config.settings import get_settings

settings = get_settings()


# ── Tool Registry ───────────────────────────────────────────────────────────
# Maps tool_id strings (stored in AgentConfig.tools JSON) to callable Python
# functions. Add a new tool here to make it available to all agents without
# touching any agent-specific code.

def _tool_forecast_version(project_id: str, **kwargs) -> Any:
    """Fetch all plan versions for a project ordered by version_number DESC."""
    from app.services.forecast_version_service import get_plan_versions
    return get_plan_versions(project_id)


def _tool_metrics_calculator(project_id: str, **kwargs) -> Any:
    """Fetch the latest ForecastMetricSnapshot for a project."""
    from app.services.metrics_service import get_latest_metrics
    return get_latest_metrics(project_id)


def _tool_raid_fetch(project_id: str, **kwargs) -> Any:
    """Fetch all open RAID items for a project."""
    from app.services.raid_service import get_raid_items
    return get_raid_items(project_id)


def _tool_rag_search(query: str, project_id: str, **kwargs) -> Any:
    """Perform semantic RAG search in ChromaDB for a project's documents."""
    try:
        from app.rag.retrieval import similarity_search
        collection_name = f"project_{project_id}_contracts"
        return similarity_search(collection_name, query, k=6)
    except Exception as e:
        return f"RAG search unavailable: {e}"


def _tool_revenue_recognition(project_id: str, **kwargs) -> Any:
    """Run revenue recognition calculation for a project."""
    from app.services.revenue_recognition_service import calculate_recognition
    return calculate_recognition(project_id)


def _tool_data_quality(project_id: str, **kwargs) -> Any:
    """Run data quality checks for a project."""
    from app.services.data_quality_service import run_quality_checks
    return run_quality_checks(project_id)


def _tool_approval_gate(agent_id: str, project_id: str, payload: Any, **kwargs) -> dict:
    """Write a pending approval request to HumanApprovalQueue."""
    conn = sqlite3.connect(settings.db_abs_path)
    approval_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO HumanApprovalQueue
            (approval_id, project_id, approval_type, title, proposed_payload,
             status, requested_by_agent, created_at)
        VALUES (?, ?, ?, ?, ?, 'Pending', ?, CURRENT_TIMESTAMP)
        """,
        (
            approval_id, project_id, agent_id,
            f"Agent Action: {agent_id}",
            json.dumps(payload, default=str),
            agent_id,
        ),
    )
    conn.commit()
    conn.close()
    return {"approval_id": approval_id, "status": "Pending"}


def _tool_summarize(
    context: Any,
    system_prompt_template: str,
    query: str,
    **kwargs,
) -> str:
    """Call the LLM to synthesize tool outputs into a narrative report."""
    llm = get_llm()
    context_str = json.dumps(context, indent=2, default=str) if not isinstance(context, str) else context
    filled_prompt = system_prompt_template.replace("{context}", context_str).replace("{query}", query)
    response = llm.invoke([
        SystemMessage(content=filled_prompt),
        HumanMessage(content=query),
    ])
    return response.content.strip()


def _tool_send_email(context: Any, **kwargs) -> dict:
    """Placeholder: send email via Gmail API (requires approval gate first)."""
    # Full implementation wired to tools/gmail_raid_poller.py in Phase 4
    return {"status": "queued", "note": "Email dispatch requires human approval."}


TOOL_REGISTRY: dict[str, callable] = {
    "forecast_version_tool":     _tool_forecast_version,
    "metrics_calculator_tool":   _tool_metrics_calculator,
    "raid_fetch_tool":           _tool_raid_fetch,
    "rag_search_tool":           _tool_rag_search,
    "revenue_recognition_tool":  _tool_revenue_recognition,
    "data_quality_tool":         _tool_data_quality,
    "approval_gate_tool":        _tool_approval_gate,
    "summarize_tool":            _tool_summarize,
    "send_email_tool":           _tool_send_email,
}


# ── Config Loader ───────────────────────────────────────────────────────────

def _load_agent_config(agent_id: str) -> dict | None:
    """Fetch a single active agent config from the AgentConfig table."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM AgentConfig WHERE agent_id = ? AND is_active = 1",
            (agent_id,),
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


def load_all_active_agent_ids() -> list[str]:
    """Return all active agent IDs from AgentConfig. Used to build the graph dynamically."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        rows = conn.execute(
            "SELECT agent_id FROM AgentConfig WHERE is_active = 1"
        ).fetchall()
        conn.close()
        return [r[0] for r in rows]
    except Exception:
        return []


def load_trigger_keywords() -> dict[str, list[str]]:
    """
    Load all active routing keywords from TriggerKeyword table.
    Returns: { agent_id: [keyword, ...] } ordered by priority ASC.
    Replaces the hardcoded RULE_KEYWORDS dict in router.py.
    """
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        rows = conn.execute(
            """
            SELECT tk.agent_id, tk.keyword
            FROM TriggerKeyword tk
            JOIN AgentConfig ac ON tk.agent_id = ac.agent_id
            WHERE tk.is_active = 1 AND ac.is_active = 1
            ORDER BY tk.priority ASC
            """
        ).fetchall()
        conn.close()
        result: dict[str, list[str]] = {}
        for agent_id, keyword in rows:
            result.setdefault(agent_id, []).append(keyword)
        return result
    except Exception:
        return {}


def _resolve_project_uuid(identifier: str) -> str:
    """Resolve a project code (e.g. 'BOSTON-001') or customer name to the SQLite project_id UUID."""
    if not identifier:
        return ""
    import re
    # Check if already a valid UUID
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    if uuid_pattern.match(identifier):
        return identifier

    try:
        conn = sqlite3.connect(settings.db_abs_path)
        # Search by ProjectNumber, OpportunityID, customer
        row = conn.execute(
            """
            SELECT project_id FROM Project 
            WHERE ProjectNumber = ? OR OpportunityID = ? OR customer = ?
               OR ProjectNumber LIKE ? OR customer LIKE ?
            LIMIT 1
            """,
            (identifier, identifier, identifier, f"%{identifier}%", f"%{identifier}%")
        ).fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass
    return identifier


# ── Generic Agent Runner ────────────────────────────────────────────────────

class GenericAgentRunner:
    """
    Loads agent configuration from AgentConfig and executes the tool pipeline
    defined in AgentConfig.tool_execution_order.

    This single class replaces all individual specialist agent Python files.
    New agents are created by inserting a row into AgentConfig — no Python needed.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.config = _load_agent_config(agent_id)

    def run(self, state: AgentState) -> dict:
        query = state.get("query", "")
        project_id = state.get("project_id", "")
        debug = state.get("debug_log", "")
        current_outputs = state.get("agent_outputs", [])

        # 1. Validate config loaded
        if not self.config:
            return {
                "agent_outputs": current_outputs + [
                    f"⚠️ Agent `{self.agent_id}` is not configured or inactive."
                ],
                "debug_log": debug + f"\n⚠️ GenericRunner: config missing for {self.agent_id}",
            }

        agent_name = self.config["name"]
        debug += f"\n🤖 {agent_name}: starting execution"

        # 2. Extract project_id if not in state
        if not project_id:
            extracted_id = self._extract_project_id(query)
            if not extracted_id:
                return {
                    "agent_outputs": current_outputs + [
                        f"❌ Please provide a Project Number so **{agent_name}** can run."
                    ],
                    "debug_log": debug + f"\n⚠️ {agent_name}: no project identifier found.",
                }
            project_id = _resolve_project_uuid(extracted_id)
        else:
            project_id = _resolve_project_uuid(project_id)

        # 3. Execute tools in order
        tool_order: list[str] = json.loads(self.config.get("tool_execution_order") or self.config["tools"])
        accumulated_context: dict[str, Any] = {}

        for tool_id in tool_order:
            tool_fn = TOOL_REGISTRY.get(tool_id)
            if not tool_fn:
                debug += f"\n⚠️ {agent_name}: unknown tool '{tool_id}', skipping."
                continue

            try:
                if tool_id == "summarize_tool":
                    # Summarize passes accumulated context + prompt template
                    result = tool_fn(
                        context=accumulated_context,
                        system_prompt_template=self.config["system_prompt_template"],
                        query=query,
                        project_id=project_id,
                    )
                elif tool_id == "approval_gate_tool":
                    if self.config.get("requires_approval"):
                        result = tool_fn(
                            agent_id=self.agent_id,
                            project_id=project_id,
                            payload=accumulated_context,
                        )
                    else:
                        continue
                elif tool_id == "rag_search_tool":
                    result = tool_fn(query=query, project_id=project_id)
                else:
                    result = tool_fn(project_id=project_id)

                accumulated_context[tool_id] = result
                debug += f"\n  ✔ {tool_id}: completed"

            except Exception as e:
                debug += f"\n  ✖ {tool_id}: failed — {e}"
                accumulated_context[tool_id] = f"Error: {e}"

        # 4. Build final report from summarize_tool output (if present)
        summary = accumulated_context.get("summarize_tool", "")
        if not summary:
            summary = json.dumps(accumulated_context, indent=2, default=str)

        report = f"--- {agent_name} Report ---\n{summary}"

        return {
            "response": summary,
            "agent_outputs": current_outputs + [report],
            "debug_log": debug + f"\n✅ {agent_name}: completed.",
            "project_id": project_id,
        }

    def _extract_project_id(self, query: str) -> str:
        """Use the LLM to extract a project number from the query."""
        llm = get_llm()
        try:
            response = llm.invoke([
                SystemMessage(content=(
                    "Extract the Project Number from this query. "
                    "Return ONLY the raw identifier string (e.g. '202021'). "
                    "Return NONE if not present."
                )),
                HumanMessage(content=query),
            ])
            result = response.content.strip()
            return "" if result in ("NONE", "none", "") else result
        except Exception:
            return ""


# ── Node Factory ────────────────────────────────────────────────────────────

def make_agent_node(agent_id: str):
    """
    Factory that creates a LangGraph-compatible node function for any agent_id.

    Usage in supervisor_graph.py:
        workflow.add_node("mbr_summary_agent", make_agent_node("mbr_summary_agent"))
    """
    def node(state: AgentState) -> dict:
        runner = GenericAgentRunner(agent_id)
        return runner.run(state)
    node.__name__ = f"{agent_id}_node"
    return node

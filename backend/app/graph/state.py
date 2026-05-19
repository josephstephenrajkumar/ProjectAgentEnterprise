"""
AgentState: the shared state schema flowing through the LangGraph DAG.

Expanded from the original orchestrator/state.py to include:
- Short-term memory fields (project_id, plan_version_id, reporting_month)
- Partial-failure Result|Error fields for mixed routing
- Operation mode for chat vs autonomous workflows
"""
from typing import TypedDict, List, Optional, Any


class AgentState(TypedDict):
    # ── Core chat fields ────────────────────────────────────────────────────
    # The user's input question
    query: str
    # Final synthesized answer returned to the user
    response: str
    # Router decision: which agent(s) to invoke
    next_node: str
    # Accumulated per-agent reports (for multi-agent synthesis)
    agent_outputs: List[str]
    # Conversation history
    history: List[dict]
    # Execution trace for the debug panel
    debug_log: str

    # ── Short-term memory (carried per-session) ─────────────────────────────
    project_id: Optional[str]
    project_number: Optional[str]
    plan_version_id: Optional[str]
    reporting_month: Optional[str]
    last_route: Optional[str]
    last_sql_intent: Optional[str]
    last_sql_result: Optional[Any]

    # ── Mixed-route partial results ─────────────────────────────────────────
    sql_result: Optional[Any]       # Result | Error from SQL Agent
    rag_result: Optional[Any]       # Result | Error from RAG Agent
    sql_error: Optional[str]
    rag_error: Optional[str]

    # ── Project-creation fields ─────────────────────────────────────────────
    project_name: Optional[str]
    project_code: Optional[str]
    opportunity_id: Optional[str]
    uploaded_files: Optional[List[str]]
    extracted_data: Optional[dict]
    user_confirmed: Optional[bool]
    operation_mode: Optional[str]         # "chat" | "create_project" | "forecast_uploaded"
    collection_names: Optional[List[str]]

    # ── Autonomous workflow fields ──────────────────────────────────────────
    workflow_trigger: Optional[str]
    approval_required: Optional[bool]
    approval_payload: Optional[dict]

"""
Chat API router.

Replaces the /chat endpoint from orchestrator/main.py.
Manages session history and invokes the LangGraph supervisor graph.
"""
import json
import os
from typing import List

from fastapi import APIRouter, HTTPException

from app.schemas.api import ChatRequest, ChatResponse
from app.config.settings import get_settings

router = APIRouter(prefix="/api", tags=["chat"])

settings = get_settings()

# ── Persistent session store ────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
SESSION_FILE = os.path.join(PROJECT_ROOT, "data", "sessions.json")


def _load_sessions() -> dict[str, List[dict]]:
    if not os.path.exists(SESSION_FILE):
        return {}
    try:
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sessions(sessions: dict[str, List[dict]]):
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save sessions: {e}")


SESSION_STORE = _load_sessions()


# ── History sanity anchor ───────────────────────────────────────────────────

def _build_project_anchor() -> str:
    """Fetch live project list to prevent hallucinations about deleted projects."""
    import sqlite3

    anchor = "FACT CHECK: The following projects are CURRENTLY ACTIVE in the system:\n"
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        cursor.execute("SELECT ProjectNumber, customer FROM Project")
        projects = cursor.fetchall()
        for p_num, cust in projects:
            anchor += f"- Project {p_num} (Customer: {cust}) is ACTIVE and AVAILABLE.\n"
        conn.close()
    except Exception:
        anchor += "- (Unable to reach database for fact check)\n"
    return anchor


# ── Chat endpoint ───────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Lazy import to avoid circular imports at module level
    from app.graph.supervisor_graph import chat_graph

    session_id = req.session_id or "default"
    history = SESSION_STORE.get(session_id, [])

    # Prepend project anchor (not persisted in session)
    project_anchor = _build_project_anchor()
    augmented_history = [{"role": "system", "content": project_anchor}] + history

    initial_state = {
        "query": req.query,
        "response": "",
        "next_node": "",
        "agent_outputs": [],
        "history": augmented_history,
        "debug_log": "",
        # Short-term memory passthrough
        "project_id": req.project_id,
    }

    try:
        result = chat_graph.invoke(initial_state)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Update session history
    new_response = result.get("response", "No response generated.")
    updated_history = history + [
        {"role": "user", "content": req.query},
        {"role": "assistant", "content": new_response},
    ]
    SESSION_STORE[session_id] = updated_history[-20:]
    _save_sessions(SESSION_STORE)

    # Extract agent tag
    debug = result.get("debug_log", "")
    agent_tag = "general_agent"
    agents_used = []
    for line in debug.splitlines():
        if "Router →" in line:
            agent_tag = line.split("Router →")[-1].strip()
            agents_used.append(agent_tag)

    return ChatResponse(
        response=new_response,
        route=agent_tag,
        agents_used=agents_used if agents_used else ["sql_agent"],
        debug_log=debug,
    )

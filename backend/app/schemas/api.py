"""
Pydantic schemas for the chat API.
Replaces the inline models from orchestrator/main.py.
"""
from pydantic import BaseModel
from typing import Optional, List


# ── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = "default"
    project_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatDebug(BaseModel):
    sql_memory_hit: Optional[bool] = None
    plan_version_id: Optional[str] = None
    confidence: Optional[float] = None


class ChatResponse(BaseModel):
    response: str
    route: Optional[str] = None
    agents_used: List[str] = []
    debug: Optional[ChatDebug] = None
    debug_log: Optional[str] = None


# ── Feedback ────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    user_query: str
    generated_sql: str
    score: int  # +1 helpful, -1 unhelpful


# ── Ingestion ───────────────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    status: str
    indexed: list


# ── Project creation ────────────────────────────────────────────────────────

class ProjectConfirmRequest(BaseModel):
    project_name: str
    project_code: str
    opportunity_id: str
    extracted_data: dict


# ── DB Management ───────────────────────────────────────────────────────────

class DBUpdateRequest(BaseModel):
    table_name: str
    pk_column: str
    pk_value: str
    updates: dict


# ── Forecast ────────────────────────────────────────────────────────────────

class ForecastUploadResponse(BaseModel):
    plan_version_id: str
    version_number: int
    status: str
    agent_workflow_started: bool = False


class MetricsCalculateRequest(BaseModel):
    plan_version_id: str
    reporting_month: str


class MetricsSnapshot(BaseModel):
    metric_snapshot_id: str
    itd_revenue: float = 0
    itd_cost: float = 0
    backlog_revenue: float = 0
    etc_revenue: float = 0
    etc_cost: float = 0
    eac_revenue: float = 0
    eac_cost: float = 0
    gm_amount: float = 0
    gm_percent: float = 0


# ── Agent workflow ──────────────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    workflow_name: str
    project_id: str
    plan_version_id: Optional[str] = None
    reporting_month: Optional[str] = None


# ── Approvals ───────────────────────────────────────────────────────────────

class ApprovalAction(BaseModel):
    rejection_reason: Optional[str] = None

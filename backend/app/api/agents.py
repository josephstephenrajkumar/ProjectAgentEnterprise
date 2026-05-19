"""
Agent Workflow and Approval API router.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict

from app.services.approval_service import get_pending_approvals, resolve_approval

router = APIRouter(prefix="/api/agents", tags=["agents"])

class ApprovalActionRequest(BaseModel):
    action: str  # "Approved" or "Rejected"
    resolved_by: str = "Admin"

@router.get("/approvals/pending")
def list_pending_approvals():
    """Get all pending actions requiring human authorization."""
    try:
        approvals = get_pending_approvals()
        return approvals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approvals/{approval_id}/resolve")
def resolve_pending_approval(approval_id: str, request: ApprovalActionRequest):
    """Approve or reject a pending agent action."""
    success = resolve_approval(
        approval_id=approval_id,
        action=request.action,
        resolved_by=request.resolved_by
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve approval. It may already be resolved or not exist.")
    
    return {"status": "success", "message": f"Approval {request.action.lower()} successfully."}

"""
Approval Service.
Manages the HumanApprovalQueue mechanics for authorizing or rejecting autonomous agent actions.
"""
import uuid
import sqlite3
import json
from typing import Dict, Any, List
from datetime import datetime

from app.config.settings import get_settings

settings = get_settings()

def get_pending_approvals() -> List[Dict[str, Any]]:
    """Retrieve all pending items in the approval queue."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM HumanApprovalQueue 
            WHERE status = 'Pending' 
            ORDER BY requested_at ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            d = dict(row)
            # Parse proposed changes JSON back into dict if it exists
            if d.get("proposed_changes"):
                try:
                    d["proposed_changes"] = json.loads(d["proposed_changes"])
                except Exception:
                    pass
            results.append(d)
        return results
    except Exception as e:
        print(f"Error fetching pending approvals: {e}")
        return []

def create_approval_request(
    project_id: str,
    approval_type: str,
    description: str,
    proposed_changes: Dict[str, Any],
    requested_by_agent: str = "System"
) -> str:
    """Create a new approval request in the queue."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        approval_id = str(uuid.uuid4())
        requested_at = datetime.utcnow().isoformat()
        changes_json = json.dumps(proposed_changes)
        
        cursor.execute(
            """
            INSERT INTO HumanApprovalQueue (
                approval_id, project_id, approval_type, status,
                description, proposed_changes, requested_by_agent, requested_at
            )
            VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?)
            """,
            (
                approval_id, project_id, approval_type, description,
                changes_json, requested_by_agent, requested_at
            )
        )
        conn.commit()
        conn.close()
        return approval_id
    except Exception as e:
        print(f"Error creating approval request: {e}")
        raise

def resolve_approval(approval_id: str, action: str, resolved_by: str = "Admin") -> bool:
    """Resolve an approval request (Approve or Reject)."""
    if action not in ["Approved", "Rejected"]:
        return False
        
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        resolved_at = datetime.utcnow().isoformat()
        
        cursor.execute(
            """
            UPDATE HumanApprovalQueue
            SET status = ?, resolved_by = ?, resolved_at = ?
            WHERE approval_id = ? AND status = 'Pending'
            """,
            (action, resolved_by, resolved_at, approval_id)
        )
        
        rowcount = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rowcount > 0 and action == "Approved":
            # In a full system, this would trigger an event/callback to apply the changes
            # For now, we just mark it approved.
            pass
            
        return rowcount > 0
    except Exception as e:
        print(f"Error resolving approval: {e}")
        return False

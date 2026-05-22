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
            ORDER BY created_at ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            d = dict(row)
            # Map database columns to the keys expected by the React frontend
            d["description"] = d.get("title", "")
            d["requested_at"] = d.get("created_at", "")
            
            # Map proposed_payload to proposed_changes
            if d.get("proposed_payload"):
                try:
                    d["proposed_changes"] = json.loads(d["proposed_payload"])
                except Exception:
                    d["proposed_changes"] = d["proposed_payload"]
            else:
                d["proposed_changes"] = {}
                
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
        created_at = datetime.utcnow().isoformat()
        changes_json = json.dumps(proposed_changes)
        
        cursor.execute(
            """
            INSERT INTO HumanApprovalQueue (
                approval_id, project_id, approval_type, status,
                title, proposed_payload, requested_by_agent, created_at
            )
            VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?)
            """,
            (
                approval_id, project_id, approval_type, description,
                changes_json, requested_by_agent, created_at
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
        
        # Get approval request details first
        cursor.execute(
            "SELECT approval_type, project_id, proposed_payload FROM HumanApprovalQueue WHERE approval_id = ? AND status = 'Pending'",
            (approval_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
            
        approval_type, project_id, proposed_payload = row
        
        cursor.execute(
            """
            UPDATE HumanApprovalQueue
            SET status = ?, approved_by = ?, approved_at = ?
            WHERE approval_id = ? AND status = 'Pending'
            """,
            (action, resolved_by, resolved_at, approval_id)
        )
        
        rowcount = cursor.rowcount
        
        if rowcount > 0 and action == "Approved":
            if approval_type == "WorkPackageIngestion":
                # Parse proposed payload and insert into ProjectWorkPackage
                work_packages = json.loads(proposed_payload)
                
                # Delete existing ones for this project
                cursor.execute("DELETE FROM ProjectWorkPackage WHERE project_id = ?", (project_id,))
                
                # Insert the approved work packages
                for wp in work_packages:
                    wp_id = str(uuid.uuid4())
                    cursor.execute(
                        """
                        INSERT INTO ProjectWorkPackage (
                            wp_id, project_id, phase_name, phase_order,
                            prerequisites, activities, customer_responsibilities,
                            out_of_scope, risks_mitigations, deliverables, acceptance_criteria,
                            overview, engagement_summary, scope, tech_landscape,
                            key_deliverables, missing_items, next_steps, quick_summary
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            wp_id,
                            project_id,
                            wp.get("phase_name"),
                            wp.get("phase_order"),
                            wp.get("prerequisites"),
                            wp.get("activities"),
                            wp.get("customer_responsibilities"),
                            wp.get("out_of_scope"),
                            wp.get("risks_mitigations"),
                            wp.get("deliverables"),
                            wp.get("acceptance_criteria"),
                            wp.get("overview"),
                            wp.get("engagement_summary"),
                            wp.get("scope"),
                            wp.get("tech_landscape"),
                            wp.get("key_deliverables"),
                            wp.get("missing_items"),
                            wp.get("next_steps"),
                            wp.get("quick_summary")
                        )
                    )
                print(f"[Approval Service] Successfully approved and inserted {len(work_packages)} work packages for project {project_id}")
            
            elif approval_type == "RaidItemCreation":
                # Parse proposed payload and insert into RAIDitems
                raid_details = json.loads(proposed_payload)
                raid_id = str(uuid.uuid4())
                last_update = datetime.utcnow().isoformat()
                
                cursor.execute(
                    """
                    INSERT INTO RAIDitems (
                        raidID, project_id, LastupdateDate, Type, Category, owner,
                        Description, MitigatingAction, DueDate, Status, 
                        plan_version_id, impact_area, financial_impact, schedule_impact_days, ROAM
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        raid_id,
                        project_id,
                        last_update,
                        raid_details.get("item_type", "Risk"),
                        raid_details.get("category", "General"),
                        raid_details.get("owner", "Unassigned"),
                        raid_details.get("description", ""),
                        raid_details.get("mitigating_action", ""),
                        raid_details.get("due_date"),
                        raid_details.get("status", "Open"),
                        raid_details.get("plan_version_id"),
                        raid_details.get("impact_area"),
                        float(raid_details.get("financial_impact") or 0.0),
                        int(raid_details.get("schedule_impact_days") or 0),
                        raid_details.get("roam", "")
                    )
                )
                print(f"[Approval Service] Successfully approved and inserted RAID item {raid_id} for project {project_id}")
        
        conn.commit()
        conn.close()
        return rowcount > 0
    except Exception as e:
        print(f"Error resolving approval: {e}")
        return False

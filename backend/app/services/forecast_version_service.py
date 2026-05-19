"""
Forecast Version Service.
Manages the creation, retrieval, and status updates of project plan versions.
"""
import uuid
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config.settings import get_settings

settings = get_settings()


def get_plan_versions(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve all plan versions for a given project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM ProjectPlanVersion WHERE project_id = ? ORDER BY version_number DESC",
            (project_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching plan versions: {e}")
        return []


def get_current_plan_version(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the current (active) plan version for a project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM ProjectPlanVersion WHERE project_id = ? AND is_current = 1 LIMIT 1",
            (project_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching current plan version: {e}")
        return None


def create_plan_version(
    project_id: str,
    version_name: str,
    version_type: str,
    source_type: str,
    reporting_month: str,
    as_of_date: str,
    status: str = "Draft",
    is_baseline: int = 0,
    source_file_name: Optional[str] = None,
    supersedes_plan_version_id: Optional[str] = None,
    submitted_by: str = "system"
) -> str:
    """Create a new plan version record."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        # Determine the next version number
        cursor.execute(
            "SELECT COALESCE(MAX(version_number), 0) + 1 FROM ProjectPlanVersion WHERE project_id = ?",
            (project_id,)
        )
        version_number = cursor.fetchone()[0]
        
        plan_version_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        cursor.execute(
            """
            INSERT INTO ProjectPlanVersion (
                plan_version_id, project_id, version_number, version_name, version_type,
                source_type, reporting_month, as_of_date, submitted_by, submitted_at,
                status, supersedes_plan_version_id, is_current, is_baseline, source_file_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                plan_version_id, project_id, version_number, version_name, version_type,
                source_type, reporting_month, as_of_date, submitted_by, timestamp,
                status, supersedes_plan_version_id, is_baseline, source_file_name
            )
        )
        
        conn.commit()
        conn.close()
        return plan_version_id
    except Exception as e:
        print(f"Error creating plan version: {e}")
        raise


def approve_plan_version(plan_version_id: str, approved_by: str = "system") -> bool:
    """Approve a plan version and make it the current version."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        # Find the project ID for this version
        cursor.execute(
            "SELECT project_id FROM ProjectPlanVersion WHERE plan_version_id = ?",
            (plan_version_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
            
        project_id = row[0]
        timestamp = datetime.utcnow().isoformat()
        
        # 1. Demote the existing current version
        cursor.execute(
            "UPDATE ProjectPlanVersion SET is_current = 0 WHERE project_id = ? AND is_current = 1",
            (project_id,)
        )
        
        # 2. Promote the new version
        cursor.execute(
            """
            UPDATE ProjectPlanVersion 
            SET status = 'Approved', is_current = 1, approved_by = ?, approved_at = ? 
            WHERE plan_version_id = ?
            """,
            (approved_by, timestamp, plan_version_id)
        )
        
        # 3. Update the Project record references
        cursor.execute(
            """
            UPDATE Project 
            SET current_plan_version_id = ?, current_approved_plan_version_id = ? 
            WHERE project_id = ?
            """,
            (plan_version_id, plan_version_id, project_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error approving plan version: {e}")
        return False

"""
RAID Service.
Manages Risks, Assumptions, Issues, and Dependencies (RAID).
"""
import uuid
import sqlite3
from typing import Dict, Any, List
from datetime import datetime

from app.config.settings import get_settings

settings = get_settings()


def get_raid_items(project_id: str) -> List[Dict[str, Any]]:
    """Retrieve all RAID items for a project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM RAIDitems WHERE project_id = ? ORDER BY DueDate ASC",
            (project_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching RAID items: {e}")
        return []


def create_raid_item(
    project_id: str,
    item_type: str,
    category: str,
    description: str,
    owner: str,
    due_date: str,
    mitigating_action: str = "",
    status: str = "Open",
    plan_version_id: str = None,
    impact_area: str = None,
    financial_impact: float = 0.0,
    schedule_impact_days: int = 0,
    roam: str = ""
) -> str:
    """Create a new RAID item."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
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
                raid_id, project_id, last_update, item_type, category, owner,
                description, mitigating_action, due_date, status,
                plan_version_id, impact_area, financial_impact, schedule_impact_days, roam
            )
        )
        conn.commit()
        conn.close()
        return raid_id
    except Exception as e:
        print(f"Error creating RAID item: {e}")
        raise


def update_raid_item(raid_id: str, updates: Dict[str, Any]) -> bool:
    """Update an existing RAID item."""
    if not updates:
        return True
        
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        updates["LastupdateDate"] = datetime.utcnow().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(raid_id)
        
        cursor.execute(
            f"UPDATE RAIDitems SET {set_clause} WHERE raidID = ?",
            tuple(values)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating RAID item: {e}")
        return False

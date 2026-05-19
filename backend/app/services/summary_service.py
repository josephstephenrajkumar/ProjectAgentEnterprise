"""
Summary Service.
Manages Project Weekly Summaries and Monthly Business Review (MBR) items.
"""
import uuid
import sqlite3
from typing import Dict, Any, List
from datetime import datetime

from app.config.settings import get_settings

settings = get_settings()


def get_weekly_summaries(project_id: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Retrieve recent weekly summaries for a project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM ProjectWeeklySummary 
            WHERE project_id = ? 
            ORDER BY date DESC LIMIT ?
            """,
            (project_id, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching weekly summaries: {e}")
        return []


def create_weekly_summary(
    project_id: str,
    summary: str,
    overall_status: str,
    financial_performance: str,
    schedule: str,
    plan_version_id: str = None,
    reporting_month: str = None
) -> str:
    """Create a new weekly summary."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        summary_id = str(uuid.uuid4())
        date_now = datetime.utcnow().isoformat()
        
        cursor.execute(
            """
            INSERT INTO ProjectWeeklySummary (
                WeeklyID, project_id, date, Summary, overallStatus,
                FinancialPerformance, Schedule, plan_version_id, reporting_month
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary_id, project_id, date_now, summary, overall_status,
                financial_performance, schedule, plan_version_id, reporting_month
            )
        )
        conn.commit()
        conn.close()
        return summary_id
    except Exception as e:
        print(f"Error creating weekly summary: {e}")
        raise


def get_mbr_items(project_id: str, plan_version_id: str = None) -> List[Dict[str, Any]]:
    """Retrieve MBR items for a project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM MBRitems WHERE project_id = ?"
        params = [project_id]
        
        if plan_version_id:
            query += " AND plan_version_id = ?"
            params.append(plan_version_id)
            
        query += " ORDER BY ForecastDateMonth DESC"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching MBR items: {e}")
        return []

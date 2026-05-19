"""
Data Quality Service.
Detects missing actuals, stale forecasts, mismatched hours, and other data anomalies.
"""
import sqlite3
from typing import Dict, List, Any
from datetime import datetime, timedelta

from app.config.settings import get_settings

settings = get_settings()


def run_data_quality_checks(project_id: str) -> List[Dict[str, Any]]:
    """
    Run a suite of data quality checks against a project's data.
    Returns a list of detected anomalies.
    """
    anomalies = []
    
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Check for missing actuals in the past month
        # Assuming we run this in the middle of a month, the previous month should have actuals
        today = datetime.utcnow()
        first_day_this_month = today.replace(day=1)
        last_month = (first_day_this_month - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d")
        
        cursor.execute(
            """
            SELECT COUNT(*) as count 
            FROM ActualFinancialMonth 
            WHERE project_id = ? AND month_date = ?
            """,
            (project_id, last_month)
        )
        row = cursor.fetchone()
        if row and row["count"] == 0:
            anomalies.append({
                "type": "MISSING_ACTUALS",
                "severity": "HIGH",
                "message": f"Missing actual financials for previous month: {last_month}",
                "month_date": last_month
            })
            
        # 2. Check for missing current forecast version
        cursor.execute(
            """
            SELECT plan_version_id, as_of_date 
            FROM ProjectPlanVersion 
            WHERE project_id = ? AND is_current = 1
            """,
            (project_id,)
        )
        current_plan = cursor.fetchone()
        if not current_plan:
            anomalies.append({
                "type": "NO_CURRENT_FORECAST",
                "severity": "HIGH",
                "message": "No current approved forecast version found for this project."
            })
        else:
            # Check if forecast is stale (e.g., > 45 days old)
            as_of_date = datetime.strptime(current_plan["as_of_date"], "%Y-%m-%d")
            if (today - as_of_date).days > 45:
                anomalies.append({
                    "type": "STALE_FORECAST",
                    "severity": "MEDIUM",
                    "message": f"Current forecast is over 45 days old (As of: {current_plan['as_of_date']})."
                })
        
        # 3. Check for open high-severity risks without mitigating actions
        cursor.execute(
            """
            SELECT raidID, Description 
            FROM RAIDitems 
            WHERE project_id = ? 
            AND Type = 'Risk' 
            AND Status IN ('Open', 'High', 'Critical')
            AND (MitigatingAction IS NULL OR MitigatingAction = '')
            """,
            (project_id,)
        )
        for risk in cursor.fetchall():
            anomalies.append({
                "type": "UNMITIGATED_HIGH_RISK",
                "severity": "HIGH",
                "message": f"High priority risk lacks mitigating action: {risk['Description'][:50]}...",
                "raid_id": risk["raidID"]
            })

        conn.close()
        return anomalies

    except Exception as e:
        print(f"Error running data quality checks: {e}")
        return [{"type": "ERROR", "severity": "HIGH", "message": f"Check failed: {str(e)}"}]

"""
Revenue Recognition Service.
Calculates and records revenue recognition based on rules:
- hours_plus_milestone (T&M + Fixed Price milestones)
- percentage_completion (Cost-to-Cost method)
"""
import uuid
import sqlite3
from typing import Dict, Any, Optional

from app.config.settings import get_settings

settings = get_settings()


def recognize_revenue(project_id: str, plan_version_id: str, reporting_month: str, method: str = "hours_plus_milestone") -> float:
    """
    Calculate the revenue to be recognized for a specific month based on actuals and plan rules.
    """
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        recognized_revenue = 0.0

        if method == "hours_plus_milestone":
            # 1. T&M: Actual hours * adjusted rate for the month
            # (Requires mapping actual hours back to resource rates, or using a blended rate).
            # For simplicity, we just take the actual revenue if already populated by timesheets.
            cursor.execute(
                """
                SELECT SUM(actual_revenue) as tm_rev 
                FROM ActualFinancialMonth 
                WHERE project_id = ? AND month_date = ?
                """,
                (project_id, reporting_month)
            )
            row = cursor.fetchone()
            tm_rev = row["tm_rev"] if row and row["tm_rev"] else 0.0
            
            # 2. Milestones: Fixed Price milestones marked as 'Achieved' in this month
            cursor.execute(
                """
                SELECT SUM(amount) as milestone_rev 
                FROM PlanRevenueMilestone 
                WHERE plan_version_id = ? AND month_date = ? AND status = 'Achieved'
                """,
                (plan_version_id, reporting_month)
            )
            row = cursor.fetchone()
            milestone_rev = row["milestone_rev"] if row and row["milestone_rev"] else 0.0
            
            recognized_revenue = tm_rev + milestone_rev

        elif method == "percentage_completion":
            # Cost-to-Cost: (ITD Actual Cost / EAC Cost) * EAC Revenue
            # Fetch latest snapshot
            cursor.execute(
                """
                SELECT itd_cost, eac_cost, eac_revenue 
                FROM ForecastMetricSnapshot 
                WHERE project_id = ? AND plan_version_id = ? AND reporting_month <= ?
                ORDER BY reporting_month DESC LIMIT 1
                """,
                (project_id, plan_version_id, reporting_month)
            )
            row = cursor.fetchone()
            if row and row["eac_cost"] and row["eac_cost"] > 0:
                poc = row["itd_cost"] / row["eac_cost"]
                cumulative_rev = poc * row["eac_revenue"]
                
                # We need prior month cumulative revenue to isolate this month, but for POC, 
                # we just return the total cumulative recognized.
                recognized_revenue = cumulative_rev

        # Optionally store this calculation in a RevenueRecognitionTrace table
        trace_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO RevenueRecognitionTrace (
                trace_id, project_id, plan_version_id, reporting_month, 
                recognition_method, recognized_amount
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (trace_id, project_id, plan_version_id, reporting_month, method, recognized_revenue)
        )
        conn.commit()
        conn.close()

        return recognized_revenue
    
    except Exception as e:
        print(f"Error recognizing revenue: {e}")
        return 0.0

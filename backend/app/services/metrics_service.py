"""
Metrics Service.
Calculates ETC (Estimate to Complete), EAC (Estimate at Completion), and GM (Gross Margin) metrics.
Saves calculated snapshots into the ForecastMetricSnapshot table.
"""
import uuid
import sqlite3
from typing import Dict, Any, Optional

from app.config.settings import get_settings

settings = get_settings()


def calculate_and_save_metrics(project_id: str, plan_version_id: str, reporting_month: str) -> Optional[Dict[str, Any]]:
    """
    Calculates metrics for a given plan version and saves them as a snapshot.
    EAC = ITD (Inception to Date Actuals) + ETC (Estimate to Complete)
    GM = EAC Revenue - EAC Cost
    """
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Calculate ITD (Actuals up to reporting_month)
        cursor.execute(
            """
            SELECT 
                SUM(actual_revenue) as itd_rev, 
                SUM(actual_cost) as itd_cost 
            FROM ActualFinancialMonth 
            WHERE project_id = ? AND month_date <= ?
            """,
            (project_id, reporting_month)
        )
        row_itd = cursor.fetchone()
        itd_revenue = row_itd["itd_rev"] or 0.0 if row_itd else 0.0
        itd_cost = row_itd["itd_cost"] or 0.0 if row_itd else 0.0

        # 2. Calculate ETC (Forecast after reporting_month for the given plan version)
        # Note: We aggregate from PlanMonthlySummary or PlanResourceMonth depending on schema usage.
        # Here we'll use PlanResourceMonth for resource ETC.
        cursor.execute(
            """
            SELECT 
                SUM(prm.planned_revenue) as etc_rev, 
                SUM(prm.planned_cost) as etc_cost
            FROM PlanResourceMonth prm
            JOIN PlanResource pr ON pr.plan_resource_id = prm.plan_resource_id
            WHERE pr.plan_version_id = ? AND prm.month_date > ?
            """,
            (plan_version_id, reporting_month)
        )
        row_etc_res = cursor.fetchone()
        etc_res_revenue = row_etc_res["etc_rev"] or 0.0 if row_etc_res else 0.0
        etc_res_cost = row_etc_res["etc_cost"] or 0.0 if row_etc_res else 0.0

        # Add ETC for other milestones/costs if needed (Invoices, Travel, Other Cost)
        # For simplicity, we just use resources here as the baseline.
        etc_revenue = etc_res_revenue
        etc_cost = etc_res_cost

        # 3. Calculate EAC and GM
        eac_revenue = itd_revenue + etc_revenue
        eac_cost = itd_cost + etc_cost
        
        gm_amount = eac_revenue - eac_cost
        gm_percent = (gm_amount / eac_revenue) * 100.0 if eac_revenue > 0 else 0.0

        # 4. Save to ForecastMetricSnapshot
        snapshot_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO ForecastMetricSnapshot (
                metric_snapshot_id, project_id, plan_version_id, reporting_month,
                itd_revenue, itd_cost, etc_revenue, etc_cost, 
                eac_revenue, eac_cost, gm_amount, gm_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id, project_id, plan_version_id, reporting_month,
                itd_revenue, itd_cost, etc_revenue, etc_cost,
                eac_revenue, eac_cost, gm_amount, gm_percent
            )
        )
        
        conn.commit()
        
        # 5. Return the calculated snapshot
        cursor.execute(
            "SELECT * FROM ForecastMetricSnapshot WHERE metric_snapshot_id = ?",
            (snapshot_id,)
        )
        saved_row = cursor.fetchone()
        conn.close()
        
        return dict(saved_row) if saved_row else None

    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return None


def get_latest_metrics(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent metrics snapshot for a project."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # We order by reporting_month DESC, or by an insertion timestamp if we had one.
        # Assuming reporting_month is sufficient for "latest"
        cursor.execute(
            """
            SELECT * FROM ForecastMetricSnapshot 
            WHERE project_id = ? 
            ORDER BY reporting_month DESC 
            LIMIT 1
            """,
            (project_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching latest metrics: {e}")
        return None

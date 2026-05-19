"""
Actuals Service.
Handles the ingestion and aggregation of actual time, cost, and revenue data.
"""
import uuid
import sqlite3
from typing import Dict, Any

from app.config.settings import get_settings

settings = get_settings()


def record_actuals(project_id: str, month_date: str, actual_hours: float, actual_cost: float, actual_revenue: float, actual_invoice: float) -> bool:
    """
    Record or update actual financials for a specific month.
    """
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        # Check if record already exists for this month
        cursor.execute(
            "SELECT actual_financial_id FROM ActualFinancialMonth WHERE project_id = ? AND month_date = ?",
            (project_id, month_date)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing
            cursor.execute(
                """
                UPDATE ActualFinancialMonth
                SET actual_hours = ?, actual_cost = ?, actual_revenue = ?, actual_invoice = ?
                WHERE actual_financial_id = ?
                """,
                (actual_hours, actual_cost, actual_revenue, actual_invoice, row[0])
            )
        else:
            # Insert new
            actual_financial_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO ActualFinancialMonth (
                    actual_financial_id, project_id, month_date, 
                    actual_hours, actual_cost, actual_revenue, actual_invoice
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (actual_financial_id, project_id, month_date, actual_hours, actual_cost, actual_revenue, actual_invoice)
            )
            
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error recording actuals: {e}")
        return False


def get_actuals(project_id: str, month_date: str) -> Dict[str, Any]:
    """Retrieve actual financials for a specific month."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM ActualFinancialMonth WHERE project_id = ? AND month_date = ?",
            (project_id, month_date)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}
        
    except Exception as e:
        print(f"Error retrieving actuals: {e}")
        return {}

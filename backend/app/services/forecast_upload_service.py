"""
Forecast Upload Service.
Handles the ingestion of Excel forecast files, parsing them, and creating new plan versions.
"""
import uuid
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.forecast_version_service import create_plan_version
from app.config.settings import get_settings

settings = get_settings()


def process_forecast_upload(
    project_id: str,
    reporting_month: str,
    submitted_by: str,
    comments: str,
    file_content: bytes,
    file_name: str
) -> Dict[str, Any]:
    """
    Process an uploaded Excel forecast.
    Parses the file, inserts the data into the plan schema, and creates a new PlanVersion.
    """
    # 1. Create a new plan version in "Draft" or "Submitted" state
    as_of_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    plan_version_id = create_plan_version(
        project_id=project_id,
        version_name=f"Forecast Upload - {reporting_month}",
        version_type="PM_REFORECAST",
        source_type="EXCEL_UPLOAD",
        reporting_month=reporting_month,
        as_of_date=as_of_date,
        status="Submitted",
        source_file_name=file_name,
        submitted_by=submitted_by
    )

    try:
        import os
        import tempfile
        from tools.excel_parser import parse_estimation_excel
        from app.services.migration_loader import parse_ddmmyyyy

        # Write file content to a temporary file
        fd, temp_path = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(file_content)
            data = parse_estimation_excel(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        # Insert resource data
        for r in data.get("resources", []):
            plan_resource_id = str(uuid.uuid4())
            adjusted_rate = float(r.get("adjusted_rate") or 0)
            cost_rate = float(r.get("cost_per_hour") or 0)
            cursor.execute(
                """
                INSERT INTO PlanResource (
                    plan_resource_id, plan_version_id, role_name, specialty, resource_name, notes,
                    location, billable, effort_needs, list_price, adjusted_rate, cost_per_hour,
                    total_hours, total_fees, total_cost
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plan_resource_id, plan_version_id, r.get("name"), r.get("specialty"),
                    None, r.get("notes"), None, r.get("billable"), float(r.get("effort_needs") or 0),
                    float(r.get("list_price") or 0), adjusted_rate, cost_rate,
                    float(r.get("total_hours") or 0), float(r.get("total_fees") or 0),
                    float(r.get("total_cost") or 0),
                ),
            )

            for month_date, hours in (r.get("monthly_hours") or {}).items():
                hours = float(hours or 0)
                cursor.execute(
                    """
                    INSERT INTO PlanResourceMonth (
                        plan_resource_month_id, plan_resource_id, month_date,
                        planned_hours, planned_revenue, planned_cost
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), plan_resource_id, month_date, hours, hours * adjusted_rate, hours * cost_rate),
                )

        # Insert invoicing milestones
        for item in data.get("invoicing", []):
            cursor.execute(
                """
                INSERT INTO PlanInvoiceMilestone (
                    plan_invoice_id, plan_version_id, detail, milestone_date, month_date,
                    type, amount, currency, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), plan_version_id, item.get("detail"), parse_ddmmyyyy(item.get("date")),
                    item.get("month_column"), item.get("type"), float(item.get("amount") or 0),
                    item.get("currency"), "Planned",
                ),
            )

        # Insert revenue milestones
        for item in data.get("revenue", []):
            cursor.execute(
                """
                INSERT INTO PlanRevenueMilestone (
                    plan_revenue_id, plan_version_id, detail, revenue_date, month_date,
                    type, amount, currency, recognition_rule, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), plan_version_id, item.get("detail"), parse_ddmmyyyy(item.get("date")),
                    item.get("month_column"), item.get("type"), float(item.get("amount") or 0),
                    item.get("currency"), "hours_plus_milestone", "Planned",
                ),
            )

        # Fetch the version number to return to the client
        cursor.execute(
            "SELECT version_number FROM ProjectPlanVersion WHERE plan_version_id = ?",
            (plan_version_id,)
        )
        row = cursor.fetchone()
        version_number = row[0] if row else 0

        conn.commit()
        conn.close()

        return {
            "plan_version_id": plan_version_id,
            "version_number": version_number,
            "status": "Submitted"
        }

    except Exception as e:
        print(f"Error processing forecast upload: {e}")
        # Delete the created plan_version_id if processing fails to prevent orphaned partial versions.
        try:
            conn = sqlite3.connect(settings.db_abs_path)
            conn.execute("DELETE FROM ProjectPlanVersion WHERE plan_version_id = ?", (plan_version_id,))
            conn.commit()
            conn.close()
        except Exception as delete_error:
            print(f"Failed to delete incomplete plan version: {delete_error}")
        raise

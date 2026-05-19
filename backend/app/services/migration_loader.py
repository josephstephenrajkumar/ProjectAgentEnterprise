"""
Migration loader service.

Ported from Migration plan/backend/app/services/migration_loader.py.
Key fix: wraps the full baseline migration in a transaction for atomicity
(addresses the migration consistency concern from the architecture review).
"""
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from app.db.engine import get_raw_connection


def new_id() -> str:
    return str(uuid.uuid4())


def safe_add_column(conn: sqlite3.Connection, table: str, column: str, ddl_type: str) -> None:
    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def apply_safe_alterations(conn: sqlite3.Connection) -> None:
    """Add new columns to existing tables without breaking them."""
    safe_add_column(conn, "Project", "current_plan_version_id", "TEXT")
    safe_add_column(conn, "Project", "current_approved_plan_version_id", "TEXT")
    safe_add_column(conn, "RAIDitems", "plan_version_id", "TEXT")
    safe_add_column(conn, "RAIDitems", "impact_area", "TEXT")
    safe_add_column(conn, "RAIDitems", "financial_impact", "REAL")
    safe_add_column(conn, "RAIDitems", "schedule_impact_days", "INTEGER")
    safe_add_column(conn, "ProjectWeeklySummary", "plan_version_id", "TEXT")
    safe_add_column(conn, "ProjectWeeklySummary", "reporting_month", "DATE")
    safe_add_column(conn, "MBRitems", "plan_version_id", "TEXT")


def parse_ddmmyyyy(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return value


def create_plan_version(
    conn: sqlite3.Connection,
    project_id: str,
    version_name: str,
    version_type: str,
    source_type: str,
    reporting_month: str,
    as_of_date: str,
    status: str = "Approved",
    is_baseline: int = 0,
    source_file_name: Optional[str] = None,
    supersedes_plan_version_id: Optional[str] = None,
    submitted_by: Optional[str] = "system",
    approved_by: Optional[str] = "system",
) -> str:
    version_number = conn.execute(
        "SELECT COALESCE(MAX(version_number), 0) + 1 FROM ProjectPlanVersion WHERE project_id = ?",
        (project_id,),
    ).fetchone()[0]

    conn.execute("UPDATE ProjectPlanVersion SET is_current = 0 WHERE project_id = ?", (project_id,))

    plan_version_id = new_id()
    conn.execute(
        """
        INSERT INTO ProjectPlanVersion (
            plan_version_id, project_id, version_number, version_name, version_type,
            source_type, reporting_month, as_of_date, submitted_by, submitted_at,
            approved_by, approved_at, status, supersedes_plan_version_id, is_current,
            is_baseline, source_file_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP, ?, ?, 1, ?, ?)
        """,
        (
            plan_version_id, project_id, version_number, version_name, version_type,
            source_type, reporting_month, as_of_date, submitted_by, approved_by,
            status, supersedes_plan_version_id, is_baseline, source_file_name,
        ),
    )
    return plan_version_id


def migrate_project_baseline(project_id: str) -> str:
    """Migrate a project's baseline JSON into the relational plan tables.

    IMPORTANT: This runs inside a transaction. If any step fails,
    the entire migration is rolled back (addresses migration consistency concern).
    """
    conn = get_raw_connection()
    conn.row_factory = sqlite3.Row

    try:
        project = conn.execute("SELECT * FROM Project WHERE project_id = ?", (project_id,)).fetchone()
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Check if already migrated
        existing = conn.execute(
            "SELECT plan_version_id FROM ProjectPlanVersion WHERE project_id = ? AND version_type = 'SALES_BASELINE'",
            (project_id,),
        ).fetchone()
        if existing:
            conn.close()
            return existing[0]

        # Begin explicit transaction
        conn.execute("BEGIN")

        reporting_month = project["startdateBaseline"] if "startdateBaseline" in project.keys() else "2026-04-01"

        plan_version_id = create_plan_version(
            conn, project_id, "Sales Baseline", "SALES_BASELINE", "SYSTEM_JSON",
            reporting_month, reporting_month, "Approved", 1,
        )

        resources = json.loads(project["resources_json"] or "[]")
        invoice_items = json.loads(project["invoice_json"] or "[]")
        revenue_items = json.loads(project["revenue_json"] or "[]")

        for r in resources:
            plan_resource_id = new_id()
            adjusted_rate = float(r.get("adjusted_rate") or 0)
            cost_rate = float(r.get("cost_per_hour") or 0)
            conn.execute(
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
                conn.execute(
                    """
                    INSERT INTO PlanResourceMonth (
                        plan_resource_month_id, plan_resource_id, month_date,
                        planned_hours, planned_revenue, planned_cost
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (new_id(), plan_resource_id, month_date, hours, hours * adjusted_rate, hours * cost_rate),
                )

        for item in invoice_items:
            conn.execute(
                """
                INSERT INTO PlanInvoiceMilestone (
                    plan_invoice_id, plan_version_id, detail, milestone_date, month_date,
                    type, amount, currency, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(), plan_version_id, item.get("detail"), parse_ddmmyyyy(item.get("date")),
                    item.get("month_column"), item.get("type"), float(item.get("amount") or 0),
                    item.get("currency"), "Planned",
                ),
            )

        for item in revenue_items:
            conn.execute(
                """
                INSERT INTO PlanRevenueMilestone (
                    plan_revenue_id, plan_version_id, detail, revenue_date, month_date,
                    type, amount, currency, recognition_rule, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id(), plan_version_id, item.get("detail"), parse_ddmmyyyy(item.get("date")),
                    item.get("month_column"), item.get("type"), float(item.get("amount") or 0),
                    item.get("currency"), "hours_plus_milestone", "Planned",
                ),
            )

        conn.execute(
            "UPDATE Project SET current_plan_version_id = ?, current_approved_plan_version_id = ? WHERE project_id = ?",
            (plan_version_id, plan_version_id, project_id),
        )

        conn.commit()
        return plan_version_id

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

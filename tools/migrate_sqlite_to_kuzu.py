"""
Migration & Graph Schema Setup Script: SQLite to KuzuDB (Phase 1)

This script demonstrates how to:
1. Initialize a local KuzuDB database schema (Node tables and Relationship tables).
2. Connect to the active SQLite database ('data/openclaw.db').
3. Extract relational records: Projects, Resources, Milestones, and RAID items.
4. Transform and load them into KuzuDB as nodes and edges.

Pre-requisites:
    pip install kuzu
"""

import os
import sqlite3
import shutil
from datetime import datetime

# We check if kuzu is installed; if not, we define a stub or log instruction
try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False


def create_kuzu_schema(db):
    """Defines the Node tables and Relationship tables in KuzuDB."""
    print("Initializing KuzuDB Graph Schema...")
    conn = kuzu.Connection(db)

    # 1. Define Node Tables
    print("Creating Node Tables...")
    
    # Project node table
    conn.execute(
        "CREATE NODE TABLE Project(id STRING, project_number STRING, customer STRING, PRIMARY KEY (id))"
    )
    
    # Resource node table
    conn.execute(
        "CREATE NODE TABLE Resource(id STRING, role_name STRING, specialty STRING, total_hours DOUBLE, total_cost DOUBLE, PRIMARY KEY (id))"
    )
    
    # Milestone node table
    conn.execute(
        "CREATE NODE TABLE Milestone(id STRING, detail STRING, amount DOUBLE, milestone_date STRING, PRIMARY KEY (id))"
    )
    
    # RAID (Risk, Assumption, Issue, Dependency) node table
    conn.execute(
        "CREATE NODE TABLE RAIDItem(id STRING, type STRING, category STRING, description STRING, status STRING, PRIMARY KEY (id))"
    )

    # 2. Define Relationship Tables (Edges)
    print("Creating Relationship Tables...")
    
    # Project -> Milestone (1-to-many relationship)
    conn.execute(
        "CREATE REL TABLE HAS_MILESTONE(FROM Project TO Milestone)"
    )
    
    # Project -> Resource (1-to-many relationship)
    conn.execute(
        "CREATE REL TABLE HAS_RESOURCE(FROM Project TO Resource)"
    )
    
    # Resource -> Milestone (many-to-many assignment relationship)
    conn.execute(
        "CREATE REL TABLE ASSIGNED_TO(FROM Resource TO Milestone, hours_allocated DOUBLE)"
    )
    
    # Project -> RAIDItem (1-to-many relationship)
    conn.execute(
        "CREATE REL TABLE HAS_RAID_ITEM(FROM Project TO RAIDItem)"
    )
    
    print("✅ KuzuDB schema successfully created!")


def migrate_data():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    # 1. Resolve paths
    sqlite_db_path = os.getenv("SQLITE_DB_PATH", "./data/openclaw.db")
    if not os.path.isabs(sqlite_db_path):
        sqlite_db_path = os.path.abspath(os.path.join(project_root, sqlite_db_path))
        
    kuzu_db_dir = os.path.abspath(os.path.join(project_root, "data", "kuzudb"))

    print(f"Reading from SQLite database: {sqlite_db_path}")
    print(f"Writing to KuzuDB directory: {kuzu_db_dir}")

    if not KUZU_AVAILABLE:
        print("\n⚠️  Error: 'kuzu' library is not installed in the python environment.")
        print("To run this migration, execute:")
        print("   pip install kuzu")
        print("\nShowing code extraction planning instead:\n")
        
    # Re-create clean Kuzu directory
    if KUZU_AVAILABLE:
        if os.path.exists(kuzu_db_dir):
            shutil.rmtree(kuzu_db_dir)
        os.makedirs(kuzu_db_dir, exist_ok=True)
        db = kuzu.Database(kuzu_db_dir)
        create_kuzu_schema(db)
        kuzu_conn = kuzu.Connection(db)
    else:
        kuzu_conn = None

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_db_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    try:
        # Extract Projects
        print("\n[ETL] Migrating Projects...")
        sqlite_cursor.execute("SELECT project_id, ProjectNumber, customer FROM Project")
        projects = sqlite_cursor.fetchall()
        for p in projects:
            p_id = p["project_id"]
            p_num = p["ProjectNumber"] or ""
            p_cust = p["customer"] or ""
            print(f"  -> Project: {p_num} ({p_cust})")
            if kuzu_conn:
                kuzu_conn.execute(
                    "CREATE (a:Project {id: $id, project_number: $num, customer: $cust})",
                    {"id": p_id, "num": p_num, "cust": p_cust}
                )

        # Extract Milestones (from PlanInvoiceMilestone)
        print("\n[ETL] Migrating Milestones...")
        sqlite_cursor.execute(
            """
            SELECT pim.plan_invoice_id, ppv.project_id, pim.detail, pim.amount, pim.milestone_date
            FROM PlanInvoiceMilestone pim
            JOIN ProjectPlanVersion ppv ON pim.plan_version_id = ppv.plan_version_id
            """
        )
        milestones = sqlite_cursor.fetchall()
        for m in milestones:
            m_id = m["plan_invoice_id"]
            p_id = m["project_id"]
            detail = m["detail"] or ""
            amount = float(m["amount"] or 0.0)
            m_date = m["milestone_date"] or ""
            print(f"  -> Milestone: {detail} (${amount})")
            if kuzu_conn:
                kuzu_conn.execute(
                    "CREATE (m:Milestone {id: $id, detail: $detail, amount: $amount, milestone_date: $m_date})",
                    {"id": m_id, "detail": detail, "amount": amount, "m_date": m_date}
                )
                kuzu_conn.execute(
                    "MATCH (p:Project), (m:Milestone) WHERE p.id = $p_id AND m.id = $m_id CREATE (p)-[:HAS_MILESTONE]->(m)",
                    {"p_id": p_id, "m_id": m_id}
                )

        # Extract Resources (from PlanResource)
        print("\n[ETL] Migrating Resources...")
        sqlite_cursor.execute(
            """
            SELECT pr.plan_resource_id, ppv.project_id, pr.role_name, pr.specialty, pr.total_hours, pr.total_cost
            FROM PlanResource pr
            JOIN ProjectPlanVersion ppv ON pr.plan_version_id = ppv.plan_version_id
            """
        )
        resources = sqlite_cursor.fetchall()
        for r in resources:
            r_id = r["plan_resource_id"]
            p_id = r["project_id"]
            role = r["role_name"] or ""
            spec = r["specialty"] or ""
            hours = float(r["total_hours"] or 0.0)
            cost = float(r["total_cost"] or 0.0)
            print(f"  -> Resource: {role} ({spec}) - {hours} hrs")
            if kuzu_conn:
                kuzu_conn.execute(
                    "CREATE (r:Resource {id: $id, role_name: $role, specialty: $spec, total_hours: $hours, total_cost: $cost})",
                    {"id": r_id, "role": role, "spec": spec, "hours": hours, "cost": cost}
                )
                kuzu_conn.execute(
                    "MATCH (p:Project), (r:Resource) WHERE p.id = $p_id AND r.id = $r_id CREATE (p)-[:HAS_RESOURCE]->(r)",
                    {"p_id": p_id, "r_id": r_id}
                )

        # Extract RAID items
        print("\n[ETL] Migrating RAID Items...")
        sqlite_cursor.execute("SELECT raidID, project_id, Type, Category, Description, Status FROM RAIDitems")
        raids = sqlite_cursor.fetchall()
        for raid in raids:
            r_id = raid["raidID"]
            p_id = raid["project_id"]
            rtype = raid["Type"] or ""
            rcat = raid["Category"] or ""
            desc = raid["Description"] or ""
            status = raid["Status"] or ""
            print(f"  -> RAID Item ({rtype}): {desc[:50]}...")
            if kuzu_conn:
                kuzu_conn.execute(
                    "CREATE (ri:RAIDItem {id: $id, type: $type, category: $cat, description: $desc, status: $status})",
                    {"id": r_id, "type": rtype, "cat": rcat, "desc": desc, "status": status}
                )
                kuzu_conn.execute(
                    "MATCH (p:Project), (ri:RAIDItem) WHERE p.id = $p_id AND ri.id = $r_id CREATE (p)-[:HAS_RAID_ITEM]->(ri)",
                    {"p_id": p_id, "r_id": r_id}
                )

        print("\n✅ Data migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration Process Failed: {e}")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    migrate_data()

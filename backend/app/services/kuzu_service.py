"""
KuzuDB Integration Service (Phase 1)

Manages KuzuDB connection lifecycle, property graph schema initialization,
and real-time synchronization hooks between SQLite (System of Record)
and KuzuDB (Read-Optimized Graph Projection).
"""
import os
import shutil
import sqlite3
import gc
from typing import Optional

from app.config.settings import get_settings

# Check if kuzu is installed
try:
    import kuzu
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False

settings = get_settings()

_db: Optional[kuzu.Database] = None

def get_kuzu_db() -> kuzu.Database:
    """Retrieve or initialize the global KuzuDB Database instance."""
    global _db
    if not KUZU_AVAILABLE:
        raise RuntimeError("The 'kuzu' package is not installed. Run 'pip install kuzu' first.")
    
    if _db is None:
        db_dir = settings.kuzu_abs_path
        # Create parent directory only. Kuzu will fail if the target database path is an empty directory.
        os.makedirs(os.path.dirname(db_dir), exist_ok=True)
        _db = kuzu.Database(db_dir)
    return _db


def close_kuzu_db() -> None:
    """Close the database and clear the reference to release directory locks."""
    global _db
    if _db is not None:
        try:
            # KuzuDB Database has a close() method to release lock
            _db.close()
        except Exception as e:
            print(f"[KuzuDB] Warning during close: {e}")
        _db = None
    # Force garbage collection to ensure file handles are released
    gc.collect()


def init_kuzu_schema(conn: kuzu.Connection) -> None:
    """Defines the Node tables and Relationship tables in KuzuDB if they do not exist."""
    print("[KuzuDB] Ensuring Graph Schema is initialized...")
    
    # 1. Define Node Tables
    # We try-except table creation since KuzuDB does not support 'CREATE TABLE IF NOT EXISTS'
    tables = [
        ("Project", "CREATE NODE TABLE Project(id STRING, project_number STRING, customer STRING, PRIMARY KEY (id))"),
        ("Resource", "CREATE NODE TABLE Resource(id STRING, role_name STRING, specialty STRING, total_hours DOUBLE, total_cost DOUBLE, PRIMARY KEY (id))"),
        ("Milestone", "CREATE NODE TABLE Milestone(id STRING, detail STRING, amount DOUBLE, milestone_date STRING, PRIMARY KEY (id))"),
        ("RAIDItem", "CREATE NODE TABLE RAIDItem(id STRING, type STRING, category STRING, description STRING, status STRING, PRIMARY KEY (id))")
    ]
    
    for t_name, query in tables:
        try:
            conn.execute(query)
            print(f"[KuzuDB] Created node table: {t_name}")
        except Exception as e:
            # Table already exists or other error
            if "already exists" not in str(e).lower():
                print(f"[KuzuDB] Node table creation info: {e}")

    # 2. Define Relationship Tables (Edges)
    rels = [
        ("HAS_MILESTONE", "CREATE REL TABLE HAS_MILESTONE(FROM Project TO Milestone)"),
        ("HAS_RESOURCE", "CREATE REL TABLE HAS_RESOURCE(FROM Project TO Resource)"),
        ("ASSIGNED_TO", "CREATE REL TABLE ASSIGNED_TO(FROM Resource TO Milestone, hours_allocated DOUBLE)"),
        ("HAS_RAID_ITEM", "CREATE REL TABLE HAS_RAID_ITEM(FROM Project TO RAIDItem)")
    ]
    
    for r_name, query in rels:
        try:
            conn.execute(query)
            print(f"[KuzuDB] Created relationship table: {r_name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                print(f"[KuzuDB] Rel table creation info: {e}")


def sync_project_to_kuzu(project_id: str) -> None:
    """Extracts a single project and its associated milestones, resources, and RAID items
    from SQLite, and upserts them into KuzuDB."""
    if not KUZU_AVAILABLE:
        print("[KuzuDB] Sync skipped: kuzu library not installed.")
        return

    # First, connect to SQLite to fetch the latest state
    sqlite_conn = sqlite3.connect(settings.db_abs_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    try:
        # Fetch Project from SQLite
        sqlite_cursor.execute("SELECT project_id, ProjectNumber, customer FROM Project WHERE project_id = ?", (project_id,))
        p = sqlite_cursor.fetchone()
        if not p:
            print(f"[KuzuDB] Project {project_id} not found in SQLite. Skipping KuzuDB sync.")
            return

        p_id = p["project_id"]
        p_num = p["ProjectNumber"] or ""
        p_cust = p["customer"] or ""

        db = get_kuzu_db()
        conn = kuzu.Connection(db)
        init_kuzu_schema(conn)

        print(f"[KuzuDB] Syncing project {p_num} ({p_id})...")

        # 1. Clean existing records for this project to perform a clean upsert
        delete_project_from_kuzu(project_id)

        # 2. Create Project Node
        conn.execute(
            "CREATE (a:Project {id: $id, project_number: $num, customer: $cust})",
            {"id": p_id, "num": p_num, "cust": p_cust}
        )

        # 3. Fetch and insert Milestones (PlanInvoiceMilestone)
        sqlite_cursor.execute(
            """
            SELECT pim.plan_invoice_id, pim.detail, pim.amount, pim.milestone_date
            FROM PlanInvoiceMilestone pim
            JOIN ProjectPlanVersion ppv ON pim.plan_version_id = ppv.plan_version_id
            WHERE ppv.project_id = ? AND ppv.is_current = 1
            """,
            (project_id,)
        )
        milestones = sqlite_cursor.fetchall()
        for m in milestones:
            m_id = m["plan_invoice_id"]
            detail = m["detail"] or ""
            amount = float(m["amount"] or 0.0)
            m_date = m["milestone_date"] or ""

            conn.execute(
                "CREATE (m:Milestone {id: $id, detail: $detail, amount: $amount, milestone_date: $m_date})",
                {"id": m_id, "detail": detail, "amount": amount, "m_date": m_date}
            )
            # Create relationship Project -> Milestone
            conn.execute(
                "MATCH (p:Project), (m:Milestone) WHERE p.id = $p_id AND m.id = $m_id CREATE (p)-[:HAS_MILESTONE]->(m)",
                {"p_id": p_id, "m_id": m_id}
            )

        # 4. Fetch and insert Resources (PlanResource)
        sqlite_cursor.execute(
            """
            SELECT pr.plan_resource_id, pr.role_name, pr.specialty, pr.total_hours, pr.total_cost
            FROM PlanResource pr
            JOIN ProjectPlanVersion ppv ON pr.plan_version_id = ppv.plan_version_id
            WHERE ppv.project_id = ? AND ppv.is_current = 1
            """,
            (project_id,)
        )
        resources = sqlite_cursor.fetchall()
        for r in resources:
            r_id = r["plan_resource_id"]
            role = r["role_name"] or ""
            spec = r["specialty"] or ""
            hours = float(r["total_hours"] or 0.0)
            cost = float(r["total_cost"] or 0.0)

            conn.execute(
                "CREATE (r:Resource {id: $id, role_name: $role, specialty: $spec, total_hours: $hours, total_cost: $cost})",
                {"id": r_id, "role": role, "spec": spec, "hours": hours, "cost": cost}
            )
            # Create relationship Project -> Resource
            conn.execute(
                "MATCH (p:Project), (r:Resource) WHERE p.id = $p_id AND r.id = $r_id CREATE (p)-[:HAS_RESOURCE]->(r)",
                {"p_id": p_id, "r_id": r_id}
            )

        # 5. Fetch and insert RAID Items
        sqlite_cursor.execute(
            "SELECT raidID, Type, Category, Description, Status FROM RAIDitems WHERE project_id = ?",
            (project_id,)
        )
        raids = sqlite_cursor.fetchall()
        for raid in raids:
            r_id = raid["raidID"]
            rtype = raid["Type"] or ""
            rcat = raid["Category"] or ""
            desc = raid["Description"] or ""
            status = raid["Status"] or ""

            conn.execute(
                "CREATE (ri:RAIDItem {id: $id, type: $type, category: $cat, description: $desc, status: $status})",
                {"id": r_id, "type": rtype, "cat": rcat, "desc": desc, "status": status}
            )
            # Create relationship Project -> RAIDItem
            conn.execute(
                "MATCH (p:Project), (ri:RAIDItem) WHERE p.id = $p_id AND ri.id = $r_id CREATE (p)-[:HAS_RAID_ITEM]->(ri)",
                {"p_id": p_id, "r_id": r_id}
            )

        print(f"[KuzuDB] ✅ Sync completed successfully for project {p_num}!")

    except Exception as e:
        print(f"[KuzuDB] ❌ Sync failed for project {project_id}: {e}")
        raise e
    finally:
        sqlite_conn.close()


def delete_project_from_kuzu(project_id: str) -> None:
    """Deletes a project node and its associated child nodes (Milestones, Resources, RAIDItems)
    from KuzuDB to maintain consistency."""
    if not KUZU_AVAILABLE:
        return

    db = get_kuzu_db()
    conn = kuzu.Connection(db)
    init_kuzu_schema(conn)

    try:
        # Delete associated Milestones
        conn.execute(
            "MATCH (p:Project {id: $p_id})-[:HAS_MILESTONE]->(m:Milestone) DETACH DELETE m",
            {"p_id": project_id}
        )
        # Delete associated Resources
        conn.execute(
            "MATCH (p:Project {id: $p_id})-[:HAS_RESOURCE]->(r:Resource) DETACH DELETE r",
            {"p_id": project_id}
        )
        # Delete associated RAIDItems
        conn.execute(
            "MATCH (p:Project {id: $p_id})-[:HAS_RAID_ITEM]->(ri:RAIDItem) DETACH DELETE ri",
            {"p_id": project_id}
        )
        # Delete Project Node itself
        conn.execute(
            "MATCH (p:Project {id: $p_id}) DETACH DELETE p",
            {"p_id": project_id}
        )
        print(f"[KuzuDB] Successfully deleted project sub-graph for {project_id}")
    except Exception as e:
        # If nodes/relations don't exist yet, we ignore it
        print(f"[KuzuDB] Project deletion cleanup info: {e}")


def recreate_kuzudb() -> None:
    """Wipes the local KuzuDB directory, recreates the schema, and migrates all data from SQLite."""
    if not KUZU_AVAILABLE:
        raise RuntimeError("The 'kuzu' package is not installed. Run 'pip install kuzu' first.")

    # 1. Close current DB connection to release lock
    close_kuzu_db()

    # 2. Delete directory
    db_dir = settings.kuzu_abs_path
    if os.path.exists(db_dir):
        print(f"[KuzuDB] Wiping existing KuzuDB directory: {db_dir}")
        shutil.rmtree(db_dir, ignore_errors=True)
    
    # Create parent directory only. Kuzu will fail if the target database path is an empty directory.
    os.makedirs(os.path.dirname(db_dir), exist_ok=True)

    # 3. Create schema
    db = get_kuzu_db()
    conn = kuzu.Connection(db)
    init_kuzu_schema(conn)

    # 4. Connect to SQLite to read all projects
    sqlite_conn = sqlite3.connect(settings.db_abs_path)
    sqlite_cursor = sqlite_conn.cursor()
    try:
        sqlite_cursor.execute("SELECT project_id FROM Project")
        projects = sqlite_cursor.fetchall()
        print(f"[KuzuDB] Found {len(projects)} projects to migrate.")
        for p in projects:
            p_id = p[0]
            # Use our sync helper
            sync_project_to_kuzu(p_id)
        print("[KuzuDB] ✅ Database fully re-created and populated!")
    finally:
        sqlite_conn.close()

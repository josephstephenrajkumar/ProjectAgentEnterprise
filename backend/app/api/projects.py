"""
Project Ingestion API.

Handles creation of new projects from the React CreateProject page.
Accepts project metadata + file uploads (SOW .docx/.pdf, estimation .xlsx,
optional ERP project .xlsx) and runs the full ingestion pipeline:

  1. Create Project record in SQLite
  2. Save uploaded files to disk under data/docs/projects/<project_id>/
  3. Parse the estimation Excel → PlanResource, PlanResourceMonth,
     PlanInvoiceMilestone, PlanRevenueMilestone, PlanMonthlySummary
  4. Vectorize the SOW document into ChromaDB (background task)
  5. Return project_id + plan_version_id to frontend

All heavy parsing runs as a FastAPI BackgroundTask so the HTTP response
returns immediately after the DB record is created.
"""

import os
import uuid
import shutil
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse

from app.config.settings import get_settings

settings = get_settings()
router = APIRouter(prefix="/api", tags=["projects"])


# ── Helpers ────────────────────────────────────────────────────────────────

def _new_id() -> str:
    return str(uuid.uuid4())


def _save_upload(file_bytes: bytes, dest_path: str) -> None:
    """Write uploaded bytes to disk, creating parent directories as needed."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)


def _create_project_record(
    project_id: str,
    project_name: str,
    project_code: str,
    opportunity_id: Optional[str],
    vectorization_status: str = "idle",
) -> None:
    """Insert a new Project row into SQLite, deleting any existing project with the same code first to ensure a clean slate."""
    conn = sqlite3.connect(settings.db_abs_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        # Check if project with this code already exists
        existing = conn.execute(
            "SELECT project_id FROM Project WHERE ProjectNumber = ?",
            (project_code,)
        ).fetchone()
        if existing:
            existing_id = existing[0]
            # Delete from SQLite manually to cascade deletes
            conn.execute("DELETE FROM ProjectPlanVersion WHERE project_id = ?", (existing_id,))
            conn.execute("DELETE FROM ActualFinancialMonth WHERE project_id = ?", (existing_id,))
            conn.execute("DELETE FROM ForecastMetricSnapshot WHERE project_id = ?", (existing_id,))
            conn.execute("DELETE FROM RevenueRecognitionTrace WHERE project_id = ?", (existing_id,))
            conn.execute("DELETE FROM Project WHERE project_id = ?", (existing_id,))
            conn.commit()
            
            # Clean up KuzuDB projection
            try:
                from app.services.kuzu_service import delete_project_from_kuzu
                delete_project_from_kuzu(existing_id)
            except Exception as e:
                print(f"[Idempotent Cleanup] ⚠️ Failed to delete project {existing_id} from KuzuDB: {e}")

            # Clean up ChromaDB collection
            try:
                import chromadb
                client = chromadb.PersistentClient(path=settings.chroma_abs_path)
                collection_name = f"project_{existing_id}_contracts"
                try:
                    client.delete_collection(collection_name)
                    print(f"[Idempotent Cleanup] Cleaned up ChromaDB collection: {collection_name}")
                except Exception:
                    pass
            except Exception as e:
                print(f"[Idempotent Cleanup] ⚠️ Failed to delete ChromaDB collection for project {existing_id}: {e}")

            # Clean up files from disk
            project_dir = os.path.join(
                settings.db_abs_path.replace("openclaw.db", ""),
                "docs", "projects", existing_id
            )
            if os.path.exists(project_dir):
                shutil.rmtree(project_dir, ignore_errors=True)

        conn.execute(
            """
            INSERT INTO Project (
                project_id, ProjectNumber, OpportunityID, customer,
                Proj_Stage, ActiveCurrency, created_at, vectorization_status
            )
            VALUES (?, ?, ?, ?, 'Open', 'USD', CURRENT_TIMESTAMP, ?)
            """,
            (project_id, project_code, opportunity_id or "", project_name, vectorization_status),
        )
        conn.commit()
    finally:
        conn.close()


def _update_vector_status(project_id: str, status: str, error: Optional[str] = None) -> None:
    """Update vectorization status and error message in SQLite."""
    conn = sqlite3.connect(settings.db_abs_path)
    try:
        conn.execute(
            "UPDATE Project SET vectorization_status = ?, vectorization_error = ? WHERE project_id = ?",
            (status, error, project_id),
        )
        conn.commit()
    finally:
        conn.close()


def _run_ingestion_pipeline(
    project_id: str,
    contract_path: Optional[str],
    estimation_path: Optional[str],
    project_file_path: Optional[str],
) -> None:
    """
    Background task: parse uploaded files and populate the planning tables.

    Step 1: Parse estimation Excel → PlanResource / milestones
    Step 2: Vectorize SOW document into ChromaDB
    Step 3: Parse optional ERP project file and migrate project baseline
    Step 4: Sync to KuzuDB read projection
    """
    print(f"[Ingestion] Starting pipeline for project {project_id}")
    import json

    # ── Step 1: Parse estimation Excel ──────────────────────────────────────
    if estimation_path and os.path.exists(estimation_path):
        try:
            from tools.excel_parser import parse_estimation_excel
            print(f"[Ingestion] Parsing estimation Excel: {estimation_path}")
            est_data = parse_estimation_excel(estimation_path)

            conn = sqlite3.connect(settings.db_abs_path)
            try:
                conn.execute(
                    """
                    UPDATE Project
                    SET resources_json = ?,
                        invoice_json = ?,
                        revenue_json = ?,
                        startdateBaseline = ?,
                        endDateBaseline = ?,
                        total_project_cost = ?,
                        travel_cost = ?,
                        other_cost = ?,
                        Baseline_Rev = ?,
                        Baseline_Cost = ?
                    WHERE project_id = ?
                    """,
                    (
                        json.dumps(est_data.get("resources", [])),
                        json.dumps(est_data.get("invoicing", [])),
                        json.dumps(est_data.get("revenue", [])),
                        est_data.get("startdateBaseline"),
                        est_data.get("endDateBaseline"),
                        est_data.get("total_cost"),
                        est_data.get("travel_expenses", {}).get("total", 0.0),
                        est_data.get("other_costs", {}).get("total", 0.0),
                        est_data.get("total_fees"),  # Baseline_Rev
                        est_data.get("total_cost"),  # Baseline_Cost
                        project_id
                    )
                )
                conn.commit()
                print(f"[Ingestion] Updated Project {project_id} from estimation Excel.")
            finally:
                conn.close()

            # Now run the forecast upload version creation
            from app.services.forecast_upload_service import process_forecast_upload
            with open(estimation_path, "rb") as f:
                content = f.read()
            reporting_month = datetime.utcnow().strftime("%Y-%m-01")
            result = process_forecast_upload(
                project_id=project_id,
                reporting_month=reporting_month,
                submitted_by="system",
                comments="Initial baseline from project ingestion",
                file_content=content,
                file_name=os.path.basename(estimation_path),
            )
            print(f"[Ingestion] Estimation parsed. Plan version: {result.get('plan_version_id')}")
        except Exception as e:
            print(f"[Ingestion] ⚠️ Estimation parsing/upload failed: {e}")

    # ── Step 2: Vectorize SOW into ChromaDB ─────────────────────────────────
    if contract_path and os.path.exists(contract_path):
        try:
            from app.rag.ingestor import ingest_document
            collection_name = f"project_{project_id}_contracts"
            ingest_document(
                file_path=contract_path,
                collection_name=collection_name,
                metadata={"project_id": project_id, "doc_type": "SOW"},
            )
            print(f"[Ingestion] SOW vectorized into collection: {collection_name}")
            _update_vector_status(project_id, "completed")
        except Exception as e:
            print(f"[Ingestion] ⚠️ SOW vectorization failed: {e}")
            _update_vector_status(project_id, "failed", str(e))

    # ── Step 3: Parse optional ERP project file & Migrate baseline ──────────
    if project_file_path and os.path.exists(project_file_path):
        try:
            from tools.excel_parser import parse_erp_excel
            print(f"[Ingestion] Parsing ERP Excel: {project_file_path}")
            erp_data = parse_erp_excel(project_file_path)

            conn = sqlite3.connect(settings.db_abs_path)
            try:
                cursor = conn.cursor()
                def fmt_date(d):
                    if hasattr(d, "strftime"):
                        return d.strftime("%Y-%m-%d")
                    return str(d) if d else None

                cursor.execute(
                    """
                    UPDATE Project
                    SET customer = COALESCE(?, customer),
                        Proj_Stage = COALESCE(?, Proj_Stage),
                        Prod_Grp = ?,
                        Portfolio = ?,
                        Contr_Type = ?,
                        Rev_Type = ?,
                        Region = ?,
                        CMT = ?,
                        country = ?,
                        Project_Owner = ?,
                        Delivery_Manager = ?,
                        Q2C_Ops = ?,
                        Start_Dt = ?,
                        End_Date = ?,
                        ActiveCurrency = COALESCE(?, ActiveCurrency),
                        Baseline_Rev = COALESCE(?, Baseline_Rev),
                        Baseline_Cost = COALESCE(?, Baseline_Cost),
                        SEGM_percent = ?
                    WHERE project_id = ?
                    """,
                    (
                        erp_data.get("Customer"),
                        erp_data.get("Proj. Stage"),
                        erp_data.get("Prod. Grp."),
                        erp_data.get("Portfolio"),
                        erp_data.get("Contr. Type"),
                        erp_data.get("Rev. Type"),
                        erp_data.get("Region"),
                        erp_data.get("CMT"),
                        erp_data.get("Country"),
                        erp_data.get("Project Owner"),
                        erp_data.get("Delivery Manager"),
                        erp_data.get("Q2C Ops"),
                        fmt_date(erp_data.get("Start Dt.")),
                        fmt_date(erp_data.get("End Date")),
                        erp_data.get("Currency"),
                        erp_data.get("Baseline Rev."),
                        erp_data.get("Baseline Cost."),
                        erp_data.get("SEGM%"),
                        project_id
                    )
                )
                conn.commit()
                print(f"[Ingestion] Updated Project {project_id} from ERP Excel.")
            finally:
                conn.close()
        except Exception as e:
            print(f"[Ingestion] ⚠️ ERP Excel parsing failed: {e}")

    # Migrate project baseline (SALES_BASELINE plan version)
    try:
        from app.services.migration_loader import migrate_project_baseline
        migrate_project_baseline(project_id)
        print(f"[Ingestion] Project baseline migrated for {project_id}")
    except Exception as e:
        print(f"[Ingestion] ⚠️ Project baseline migration failed: {e}")

    # ── Step 4: Sync to KuzuDB read projection ───────────────────────────────
    try:
        from app.services.kuzu_service import sync_project_to_kuzu
        sync_project_to_kuzu(project_id)
        print(f"[Ingestion] KuzuDB read projection synchronized for project {project_id}")
    except Exception as e:
        print(f"[Ingestion] ⚠️ KuzuDB synchronization failed: {e}")

    print(f"[Ingestion] ✅ Pipeline complete for project {project_id}")


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/projects")
async def create_project(
    background_tasks: BackgroundTasks,
    project_name: str = Form(...),
    project_code: str = Form(...),
    opportunity_id: Optional[str] = Form(None),
    contract_file: Optional[UploadFile] = File(None),
    estimation_file: Optional[UploadFile] = File(None),
    project_file: Optional[UploadFile] = File(None),
):
    """
    Create a new project and ingest the uploaded SOW and estimation files.

    Required form fields:
      - project_name (str)
      - project_code (str)
    Optional form fields:
      - opportunity_id (str)
    File uploads:
      - contract_file  (.docx / .doc / .pdf)  — SOW document
      - estimation_file (.xlsx)                — Resource & milestone estimates
      - project_file (.xlsx)                   — ERP project metadata
    """
    if not project_name or not project_code:
        raise HTTPException(
            status_code=422,
            detail="project_name and project_code are required."
        )

    project_id = _new_id()
    project_dir = os.path.join(
        settings.db_abs_path.replace("openclaw.db", ""),
        "docs", "projects", project_id,
    )
    os.makedirs(project_dir, exist_ok=True)

    has_contract = bool(contract_file and contract_file.filename)
    init_status = "processing" if has_contract else "idle"

    # 1. Create the Project record immediately
    try:
        _create_project_record(project_id, project_name, project_code, opportunity_id, init_status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project record: {e}")

    # 2. Save uploaded files to disk
    contract_path = None
    estimation_path = None
    project_file_path = None

    if contract_file and contract_file.filename:
        contract_path = os.path.join(project_dir, contract_file.filename)
        _save_upload(await contract_file.read(), contract_path)

    if estimation_file and estimation_file.filename:
        estimation_path = os.path.join(project_dir, estimation_file.filename)
        _save_upload(await estimation_file.read(), estimation_path)

    if project_file and project_file.filename:
        project_file_path = os.path.join(project_dir, project_file.filename)
        _save_upload(await project_file.read(), project_file_path)

    # 3. Schedule the heavy parsing pipeline as a background task
    background_tasks.add_task(
        _run_ingestion_pipeline,
        project_id,
        contract_path,
        estimation_path,
        project_file_path,
    )

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "project_id": project_id,
            "project_code": project_code,
            "project_name": project_name,
            "message": (
                f"Project '{project_name}' created. "
                "Files are being parsed and vectorized in the background."
            ),
            "files_received": {
                "contract": contract_file.filename if contract_file else None,
                "estimation": estimation_file.filename if estimation_file else None,
                "project": project_file.filename if project_file else None,
            },
        },
    )


@router.get("/projects")
def list_projects():
    """List all projects with their current plan version status."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                p.project_id,
                p.ProjectNumber,
                p.customer,
                p.Proj_Stage,
                p.OpportunityID,
                p.ActiveCurrency,
                p.current_plan_version_id,
                p.vectorization_status,
                p.vectorization_error,
                ppv.version_name   AS current_version_name,
                ppv.status         AS current_version_status,
                ppv.reporting_month
            FROM Project p
            LEFT JOIN ProjectPlanVersion ppv
                ON p.current_plan_version_id = ppv.plan_version_id
            ORDER BY p.rowid DESC
            """
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    """Get a single project by its internal UUID."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM Project WHERE project_id = ?",
            (project_id,)
        ).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/by-code/{project_code}")
def get_project_by_code(project_code: str):
    """Get a project by its ProjectNumber code (e.g. 'BOSTON-001')."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM Project WHERE ProjectNumber LIKE ?",
            (f"%{project_code}%",)
        ).fetchone()
        conn.close()
        if not row:
            raise HTTPException(status_code=404, detail=f"Project '{project_code}' not found.")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{identifier}")
def delete_project(identifier: str):
    """Permanently delete a project by its project_id, ProjectNumber, or customer name."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()
        
        # Check if project exists by id, code, or customer name
        cursor.execute(
            """
            SELECT project_id, ProjectNumber FROM Project 
            WHERE project_id = ? OR ProjectNumber = ? OR customer = ?
            """,
            (identifier, identifier, identifier)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Project '{identifier}' not found.")
        
        pid, pcode = row
        
        # Delete from SQLite (manually cascade deletes for tables lacking ON DELETE CASCADE)
        cursor.execute("DELETE FROM ProjectPlanVersion WHERE project_id = ?", (pid,))
        cursor.execute("DELETE FROM ActualFinancialMonth WHERE project_id = ?", (pid,))
        cursor.execute("DELETE FROM ForecastMetricSnapshot WHERE project_id = ?", (pid,))
        cursor.execute("DELETE FROM RevenueRecognitionTrace WHERE project_id = ?", (pid,))
        cursor.execute("DELETE FROM Project WHERE project_id = ?", (pid,))
        conn.commit()
        conn.close()

        # Also clean up KuzuDB projection
        try:
            from app.services.kuzu_service import delete_project_from_kuzu
            delete_project_from_kuzu(pid)
        except Exception as e:
            print(f"[Delete] ⚠️ Failed to delete project from KuzuDB: {e}")

        # Also clean up ChromaDB collection
        try:
            import chromadb
            client = chromadb.PersistentClient(path=settings.chroma_abs_path)
            collection_name = f"project_{pid}_contracts"
            try:
                client.delete_collection(collection_name)
                print(f"[Delete] Cleaned up ChromaDB collection: {collection_name}")
            except Exception:
                pass
        except Exception as e:
            print(f"[Delete] ⚠️ Failed to delete ChromaDB collection for project {pid}: {e}")
        
        # Also clean up the files from disk if they exist
        project_dir = os.path.join(
            settings.db_abs_path.replace("openclaw.db", ""),
            "docs", "projects", pid
        )
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
            
        return {
            "status": "success", 
            "message": f"Successfully deleted project code '{pcode}' (id: {pid}) and associated data."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting project: {e}")


@router.post("/projects/kuzudb/recreate")
def post_recreate_kuzudb():
    """Wipe KuzuDB directory and re-create all data projections from SQLite."""
    try:
        from app.services.kuzu_service import recreate_kuzudb
        recreate_kuzudb()
        return {
            "status": "success",
            "message": "KuzuDB property graph database has been successfully re-created and synchronized from SQLite system of record."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to re-create KuzuDB: {str(e)}")


@router.get("/projects/kuzudb/status")
def get_kuzudb_status():
    """Get the current synchronization status and node counts in KuzuDB."""
    try:
        from app.services.kuzu_service import KUZU_AVAILABLE, get_kuzu_db, init_kuzu_schema
        import kuzu
        
        if not KUZU_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "Kuzu library not installed",
                "counts": {}
            }
            
        db = get_kuzu_db()
        conn = kuzu.Connection(db)
        init_kuzu_schema(conn)
        
        # Count nodes
        counts = {}
        for node_table in ["Project", "Resource", "Milestone", "RAIDItem"]:
            try:
                res = conn.execute(f"MATCH (n:{node_table}) RETURN count(n)").get_next()
                counts[node_table] = res[0]
            except Exception:
                counts[node_table] = 0
                
        return {
            "status": "ready",
            "counts": counts,
            "message": "KuzuDB is active and synchronized."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "counts": {}
        }


@router.post("/projects/test/run")
async def run_e2e_tests():
    """Run E2E ingestion and chat routing tests as a subprocess."""
    import asyncio
    import subprocess
    import json
    try:
        python_bin = "/home/joseph/miniconda3/bin/python3"
        script_path = "/home/joseph/ProjectAgentEnterprise/tools/test_e2e_ingestion_chat.py"
        
        # Execute the test script using the conda Python environment
        process = await asyncio.create_subprocess_exec(
            python_bin, script_path, "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/joseph/ProjectAgentEnterprise"
        )
        stdout, stderr = await process.communicate()
        
        out_str = stdout.decode("utf-8", errors="replace")
        err_str = stderr.decode("utf-8", errors="replace")
        
        try:
            results_json = json.loads(out_str.strip())
        except Exception:
            results_json = None
            
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "returncode": process.returncode,
            "stdout": out_str,
            "stderr": err_str,
            "results": results_json
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute tests: {str(e)}")


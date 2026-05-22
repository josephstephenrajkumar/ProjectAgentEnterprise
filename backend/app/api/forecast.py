"""
Forecast API router.

Covers forecast upload, version history, approval, and metrics calculation.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List

from app.schemas.api import ForecastUploadResponse, MetricsCalculateRequest, MetricsSnapshot
from app.services.forecast_upload_service import process_forecast_upload
from app.services.forecast_version_service import get_plan_versions, get_current_plan_version, approve_plan_version
from app.services.metrics_service import calculate_and_save_metrics, get_latest_metrics

router = APIRouter(prefix="/api", tags=["forecast"])


@router.post(
    "/projects/{project_id}/forecast-upload",
    response_model=ForecastUploadResponse,
)
async def upload_forecast(
    project_id: str,
    reporting_month: str = Form(...),
    submitted_by: str = Form("PM"),
    comments: str = Form(""),
    file: UploadFile = File(...),
):
    """Upload a new forecast Excel file and create a ProjectPlanVersion."""
    try:
        content = await file.read()
        result = process_forecast_upload(
            project_id=project_id,
            reporting_month=reporting_month,
            submitted_by=submitted_by,
            comments=comments,
            file_content=content,
            file_name=file.filename
        )
        return ForecastUploadResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/forecast-versions")
def get_versions(project_id: str):
    """Return all plan versions for a project."""
    versions = get_plan_versions(project_id)
    return versions


@router.get("/projects/{project_id}/forecast-versions/current")
def get_current_forecast(project_id: str):
    """Return the current approved forecast version."""
    version = get_current_plan_version(project_id)
    if not version:
        raise HTTPException(status_code=404, detail="No current forecast version found.")
    return version


@router.post("/forecast-versions/{plan_version_id}/approve")
def approve_forecast(plan_version_id: str):
    """Approve a submitted forecast version."""
    success = approve_plan_version(plan_version_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve forecast version.")
    return {"status": "success", "message": "Forecast approved and set as current."}


@router.post(
    "/projects/{project_id}/forecast-metrics/calculate",
    response_model=MetricsSnapshot,
)
def calculate_metrics(project_id: str, req: MetricsCalculateRequest):
    """Calculate ETC/EAC/GM metrics for a project."""
    metrics = calculate_and_save_metrics(
        project_id=project_id,
        plan_version_id=req.plan_version_id,
        reporting_month=req.reporting_month
    )
    if not metrics:
        raise HTTPException(status_code=500, detail="Failed to calculate metrics.")
    return MetricsSnapshot(**metrics)


@router.get("/projects/{project_id}/forecast-metrics/latest")
def get_latest_project_metrics(project_id: str):
    """Return the most recent metrics snapshot."""
    metrics = get_latest_metrics(project_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found for this project.")
    return metrics


@router.get("/projects/{project_id}/dashboard-summary")
def get_dashboard_summary(project_id: str):
    """Retrieve latest forecast metrics and active risks for dashboard display."""
    import sqlite3
    from app.config.settings import get_settings
    from app.services.raid_service import get_raid_items
    
    settings = get_settings()
    try:
        # 1. Fetch latest metrics snapshot
        metrics = get_latest_metrics(project_id)
        
        # 2. Fetch RAID items
        raid_items = get_raid_items(project_id)
        active_risks = [r for r in raid_items if r.get("Type") == "Risk" and r.get("Status") == "Open"]
        high_priority_risks = [
            r for r in active_risks 
            if r.get("Category") in ("High", "Critical", "Red") 
            or (r.get("financial_impact") and r.get("financial_impact") > 50000)
        ]
        
        # 3. Retrieve baseline reference
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        proj = conn.execute(
            "SELECT Baseline_Rev, Baseline_Cost FROM Project WHERE project_id = ?", 
            (project_id,)
        ).fetchone()
        conn.close()
        
        baseline_rev = proj["Baseline_Rev"] if (proj and proj["Baseline_Rev"]) else 0
        baseline_cost = proj["Baseline_Cost"] if (proj and proj["Baseline_Cost"]) else 0
        
        res = {
            "eac_revenue": 0.0,
            "eac_cost": 0.0,
            "gm_percent": 0.0,
            "baseline_revenue": float(baseline_rev),
            "baseline_cost": float(baseline_cost),
            "active_risks_count": len(active_risks),
            "high_priority_risks_count": len(high_priority_risks),
            "revenue_variance_percent": 0.0,
            "gm_variance_percent": 0.0
        }
        
        if metrics:
            res["eac_revenue"] = metrics.get("eac_revenue", 0.0)
            res["eac_cost"] = metrics.get("eac_cost", 0.0)
            res["gm_percent"] = metrics.get("gm_percent", 0.0)
            
            # Calculate variance from baseline
            if baseline_rev > 0:
                res["revenue_variance_percent"] = ((res["eac_revenue"] - baseline_rev) / baseline_rev) * 100
                
            baseline_gm = ((baseline_rev - baseline_cost) / baseline_rev * 100) if baseline_rev > 0 else 0.0
            res["gm_variance_percent"] = res["gm_percent"] - baseline_gm
            
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard summary calculation error: {e}")


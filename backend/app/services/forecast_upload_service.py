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
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        
        # ---------------------------------------------------------
        # TODO: Phase 3 - Implement actual Pandas Excel parsing here
        # Example logic:
        # df_resources = pd.read_excel(file_content, sheet_name="Resources")
        # for _, row in df_resources.iterrows():
        #     # Insert into PlanResource and PlanResourceMonth
        #     pass
        # ---------------------------------------------------------

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
        # Consider deleting the created plan_version_id if processing fails
        # to prevent orphaned partial versions.
        raise

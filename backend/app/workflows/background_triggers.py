"""
Background Workflows.
Demonstrates how autonomous agents can run in the background, detect issues,
and submit actions to the Human Approval Queue.
"""
import sqlite3
from typing import List

from app.config.settings import get_settings
from app.services.data_quality_service import run_data_quality_checks
from app.services.approval_service import create_approval_request

settings = get_settings()

def get_all_active_projects() -> List[str]:
    """Fetch all active project IDs from the database."""
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        cursor = conn.cursor()
        # Fetching project_id (internal UUID) or ProjectNumber depending on schema
        cursor.execute("SELECT project_id, ProjectNumber FROM Project WHERE Status = 'Active'")
        rows = cursor.fetchall()
        conn.close()
        # We'll use ProjectNumber as the identifier for the agents
        return [row[1] for row in rows]
    except Exception as e:
        print(f"Error fetching active projects: {e}")
        return []

def nightly_data_quality_job():
    """
    Runs Data Quality checks on all active projects.
    If HIGH severity anomalies are found, it proposes an auto-correction
    via the Human Approval Queue.
    """
    print("Starting Nightly Data Quality Job...")
    active_projects = get_all_active_projects()
    
    for identifier in active_projects:
        print(f"Running DQ checks for {identifier}...")
        anomalies = run_data_quality_checks(identifier)
        
        high_severity = [a for a in anomalies if a.get("severity") == "HIGH"]
        
        if high_severity:
            # Create a summary of the issues
            description = f"Nightly scan detected {len(high_severity)} critical anomalies:\n"
            for a in high_severity:
                description += f"- [{a.get('type')}] {a.get('message')}\n"
            
            description += "\nProposed Action: Send automated alert to PM and pause automated reporting."
            
            # Queue for human review
            create_approval_request(
                project_id=identifier,
                approval_type="Data Quality Remediation",
                description=description,
                proposed_changes={"action": "pause_reporting", "alert_pm": True},
                requested_by_agent="Data Quality Agent"
            )
            print(f"⚠️ Queued approval request for {identifier}")
            
    print("Nightly Data Quality Job completed.")

if __name__ == "__main__":
    nightly_data_quality_job()

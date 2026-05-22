# Implementation Plan: UI Alert for Project Vectorization Status

This plan addresses the user's request to implement a method to notify the user in the UI via an alert whether SOW contract vectorization succeeds or fails for a newly created project.

## User Review Required

> [!IMPORTANT]
> - **Schema Migration**: We will dynamically alter the existing `Project` table to add two columns (`vectorization_status` and `vectorization_error`) on startup. This avoids breaking any existing records.
> - **Polling Frequency**: We propose a 2-second polling interval in the frontend to fetch the project's details after creation. This ensures a responsive UI without overloading the FastAPI backend.

## Proposed Changes

### Component: Database Schema

#### [MODIFY] [migration_loader.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/services/migration_loader.py)
* Add `vectorization_status` (TEXT DEFAULT 'idle') and `vectorization_error` (TEXT) columns to the `Project` table inside `apply_safe_alterations`.

#### [MODIFY] [init_sqlite_db.py](file:///home/joseph/ProjectAgentEnterprise/tools/init_sqlite_db.py)
* Update the primary SQL table creation statement for `Project` to include `vectorization_status TEXT DEFAULT 'idle'` and `vectorization_error TEXT`.

---

### Component: Backend Ingestion API

#### [MODIFY] [projects.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/api/projects.py)
* Update `_create_project_record` to accept and insert the initial `vectorization_status` ('processing' if a contract is uploaded, 'idle' otherwise).
* Add a helper `_update_vector_status(project_id, status, error)` to update the SQLite database table.
* Modify `_run_ingestion_pipeline` to:
  * Update status to `'completed'` upon successful execution of `ingest_document`.
  * Update status to `'failed'` and store the exception details in `vectorization_error` if an error occurs.
* Verify that `GET /api/projects/{project_id}` automatically returns the new columns (`vectorization_status` and `vectorization_error`) via `SELECT *`.

---

### Component: Frontend React UI

#### [MODIFY] [CreateProject.tsx](file:///home/joseph/ProjectAgentEnterprise/frontend-react/src/pages/CreateProject.tsx)
* Add component state variables to track `pollingProjectId`, `vectorizationStatus`, and `vectorizationError`.
* After a successful project creation:
  * If a SOW contract file was uploaded:
    * Save the returned `project_id` to `pollingProjectId` and set the status to `'processing'`.
    * Start an interval to poll `GET http://localhost:8000/api/projects/{project_id}` every 2 seconds.
* Design a premium, glassmorphism-styled notification banner/alert below the creation form:
  * **Processing State**: Render a loading spinner with a message indicating that the AI multi-agent system is indexing and vectorizing the contract SOW in the background.
  * **Completed State**: Render a green/emerald success card with a checkmark indicating that the SOW contract was successfully vectorized and is ready for AI analysis in the Chat Console.
  * **Failed State**: Render a crimson/red error card with an alert icon, explaining that vectorization failed, accompanied by the raw error details.
* Ensure intervals are correctly cleared when vectorization finishes (either `'completed'` or `'failed'`) and on component unmount.

---

## Verification Plan

### Automated Tests
* Build and verify the frontend:
  ```bash
  cd /home/joseph/ProjectAgentEnterprise/frontend-react && npm run build
  ```
* Run a python startup check on the backend app to ensure it loads without syntax/import issues:
  ```bash
  python -m uvicorn backend.app.main:app --help
  ```

### Manual Verification
1. Create a new project `BOSTON-TEST` and upload `Boston_Property_SMAX_Migration_SOW_v0.4.docx` and the estimation sheet.
2. Confirm the UI displays the progress banner: `"Vectorizing contract in background..."` with an animated spinner.
3. Check the backend logs/terminal to see the database updates.
4. Verify the progress banner updates to `"Contract vectorized successfully!"` (with a premium green checkmark) once indexing completes.
5. Simulate a failure case (e.g. upload a corrupt or unsupported file) or review error handling to ensure a red alert is displayed with error details.

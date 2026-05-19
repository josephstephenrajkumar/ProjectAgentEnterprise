# API Contracts

## POST /api/chat

Request:
```json
{
  "query": "What is the EAC cost for project 202021?",
  "project_id": "optional",
  "conversation_id": "optional"
}
```

Response:
```json
{
  "response": "The latest approved EAC cost is ...",
  "route": "sql",
  "agents_used": ["supervisor_router_agent", "sql_agent"],
  "debug": {
    "sql_memory_hit": true,
    "plan_version_id": "...",
    "confidence": 0.91
  }
}
```

## POST /api/projects/{project_id}/forecast-upload

Form data:
- file
- reporting_month
- submitted_by
- comments

Response:
```json
{
  "plan_version_id": "...",
  "version_number": 3,
  "status": "Submitted",
  "agent_workflow_started": true
}
```

## POST /api/projects/{project_id}/forecast-metrics/calculate

Request:
```json
{
  "plan_version_id": "...",
  "reporting_month": "2026-07-01"
}
```

Response:
```json
{
  "metric_snapshot_id": "...",
  "itd_revenue": 90350,
  "itd_cost": 60000,
  "etc_revenue": 48650,
  "etc_cost": 34913.92,
  "eac_revenue": 139000,
  "eac_cost": 94913.92,
  "gm_amount": 44086.08,
  "gm_percent": 31.72
}
```

## POST /api/agents/run-workflow

Request:
```json
{
  "workflow_name": "forecast_uploaded",
  "project_id": "...",
  "plan_version_id": "...",
  "reporting_month": "2026-07-01"
}
```

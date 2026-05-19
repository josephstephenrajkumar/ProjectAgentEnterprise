PRAGMA foreign_keys = ON;

-- Existing table alterations should be done through a safe migration helper.
-- SQLite does not support ALTER TABLE ADD COLUMN IF NOT EXISTS.
-- Required additions:
-- Project.current_plan_version_id TEXT
-- Project.current_approved_plan_version_id TEXT
-- RAIDitems.plan_version_id TEXT
-- RAIDitems.impact_area TEXT
-- RAIDitems.financial_impact REAL
-- RAIDitems.schedule_impact_days INTEGER
-- ProjectWeeklySummary.plan_version_id TEXT
-- ProjectWeeklySummary.reporting_month DATE
-- MBRitems.plan_version_id TEXT

CREATE TABLE IF NOT EXISTS ProjectPlanVersion (
    plan_version_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    version_name TEXT,
    version_type TEXT NOT NULL CHECK (version_type IN ('SALES_BASELINE','PM_INITIAL','PM_REFORECAST','SYSTEM_REFORECAST')),
    source_type TEXT NOT NULL CHECK (source_type IN ('SYSTEM_JSON','EXCEL_UPLOAD','MANUAL','AGENT_DRAFT')),
    reporting_month DATE NOT NULL,
    as_of_date DATE NOT NULL,
    submitted_by TEXT,
    submitted_at DATETIME,
    approved_by TEXT,
    approved_at DATETIME,
    status TEXT NOT NULL CHECK (status IN ('Draft','Submitted','Approved','Rejected','Superseded','Locked')),
    supersedes_plan_version_id TEXT,
    is_current INTEGER DEFAULT 0,
    is_baseline INTEGER DEFAULT 0,
    comments TEXT,
    source_file_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES Project(project_id),
    FOREIGN KEY(supersedes_plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ppv_project_version
ON ProjectPlanVersion(project_id, version_number);

CREATE INDEX IF NOT EXISTS idx_ppv_project_current
ON ProjectPlanVersion(project_id, is_current, status);

CREATE TABLE IF NOT EXISTS PlanResource (
    plan_resource_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    role_name TEXT NOT NULL,
    specialty TEXT,
    resource_name TEXT,
    notes TEXT,
    location TEXT,
    billable TEXT,
    effort_needs REAL DEFAULT 0,
    list_price REAL DEFAULT 0,
    adjusted_rate REAL DEFAULT 0,
    cost_per_hour REAL DEFAULT 0,
    total_hours REAL DEFAULT 0,
    total_fees REAL DEFAULT 0,
    total_cost REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_plan_resource_version
ON PlanResource(plan_version_id);

CREATE TABLE IF NOT EXISTS PlanResourceMonth (
    plan_resource_month_id TEXT PRIMARY KEY,
    plan_resource_id TEXT NOT NULL,
    month_date DATE NOT NULL,
    planned_hours REAL DEFAULT 0,
    planned_revenue REAL DEFAULT 0,
    planned_cost REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_resource_id) REFERENCES PlanResource(plan_resource_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_resource_month_unique
ON PlanResourceMonth(plan_resource_id, month_date);

CREATE INDEX IF NOT EXISTS idx_plan_resource_month_month
ON PlanResourceMonth(month_date);

CREATE TABLE IF NOT EXISTS PlanInvoiceMilestone (
    plan_invoice_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    milestone_date DATE,
    month_date DATE,
    type TEXT,
    amount REAL DEFAULT 0,
    currency TEXT,
    status TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS PlanRevenueMilestone (
    plan_revenue_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    revenue_date DATE,
    month_date DATE,
    type TEXT,
    amount REAL DEFAULT 0,
    currency TEXT,
    recognition_rule TEXT,
    status TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS PlanTravelCost (
    plan_travel_cost_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    resource_name TEXT,
    notes TEXT,
    month_date DATE NOT NULL,
    amount REAL DEFAULT 0,
    billable TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS PlanOtherCost (
    plan_other_cost_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    cost_name TEXT NOT NULL,
    month_date DATE NOT NULL,
    amount REAL DEFAULT 0,
    billable TEXT,
    total_fees REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS PlanMonthlySummary (
    plan_monthly_summary_id TEXT PRIMARY KEY,
    plan_version_id TEXT NOT NULL,
    month_date DATE NOT NULL,
    total_hours REAL DEFAULT 0,
    total_resource_revenue REAL DEFAULT 0,
    total_resource_cost REAL DEFAULT 0,
    total_invoice_amount REAL DEFAULT 0,
    total_revenue_amount REAL DEFAULT 0,
    total_travel_cost REAL DEFAULT 0,
    total_other_cost REAL DEFAULT 0,
    total_month_cost REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_plan_monthly_summary_unique
ON PlanMonthlySummary(plan_version_id, month_date);

CREATE TABLE IF NOT EXISTS ActualFinancialMonth (
    actual_financial_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    month_date DATE NOT NULL,
    actual_hours REAL DEFAULT 0,
    actual_cost REAL DEFAULT 0,
    actual_revenue REAL DEFAULT 0,
    actual_invoice REAL DEFAULT 0,
    actual_travel_cost REAL DEFAULT 0,
    actual_other_cost REAL DEFAULT 0,
    source TEXT,
    loaded_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(project_id) REFERENCES Project(project_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_actual_financial_project_month
ON ActualFinancialMonth(project_id, month_date);

CREATE TABLE IF NOT EXISTS ForecastMetricSnapshot (
    metric_snapshot_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    plan_version_id TEXT NOT NULL,
    reporting_month DATE NOT NULL,
    itd_revenue REAL DEFAULT 0,
    itd_cost REAL DEFAULT 0,
    backlog_revenue REAL DEFAULT 0,
    etc_revenue REAL DEFAULT 0,
    etc_cost REAL DEFAULT 0,
    eac_revenue REAL DEFAULT 0,
    eac_cost REAL DEFAULT 0,
    gm_amount REAL DEFAULT 0,
    gm_percent REAL DEFAULT 0,
    calculated_at DATETIME,
    FOREIGN KEY(project_id) REFERENCES Project(project_id),
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_metric_snapshot_unique
ON ForecastMetricSnapshot(project_id, plan_version_id, reporting_month);

CREATE TABLE IF NOT EXISTS RevenueRecognitionTrace (
    revenue_trace_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    plan_version_id TEXT NOT NULL,
    month_date DATE NOT NULL,
    actual_hours REAL DEFAULT 0,
    milestone_met INTEGER DEFAULT 0,
    recognized_revenue REAL DEFAULT 0,
    source_detail TEXT,
    calculated_at DATETIME,
    FOREIGN KEY(project_id) REFERENCES Project(project_id),
    FOREIGN KEY(plan_version_id) REFERENCES ProjectPlanVersion(plan_version_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_revenue_trace_unique
ON RevenueRecognitionTrace(project_id, plan_version_id, month_date);

CREATE TABLE IF NOT EXISTS SqlQueryMemory (
    sql_memory_id TEXT PRIMARY KEY,
    intent_name TEXT NOT NULL,
    user_query_pattern TEXT NOT NULL,
    normalized_query TEXT,
    sql_template TEXT NOT NULL,
    required_parameters TEXT,
    schema_entities TEXT,
    route_hint TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    confidence_score REAL DEFAULT 0,
    last_used_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sql_memory_intent
ON SqlQueryMemory(intent_name, confidence_score);

CREATE TABLE IF NOT EXISTS AgentActionLog (
    agent_action_id TEXT PRIMARY KEY,
    project_id TEXT,
    plan_version_id TEXT,
    agent_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    input_payload TEXT,
    output_payload TEXT,
    status TEXT,
    requires_human_approval INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS HumanApprovalQueue (
    approval_id TEXT PRIMARY KEY,
    project_id TEXT,
    plan_version_id TEXT,
    agent_action_id TEXT,
    approval_type TEXT NOT NULL,
    title TEXT NOT NULL,
    proposed_payload TEXT,
    status TEXT DEFAULT 'Pending',
    requested_by_agent TEXT,
    approved_by TEXT,
    approved_at DATETIME,
    rejection_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(agent_action_id) REFERENCES AgentActionLog(agent_action_id)
);

CREATE INDEX IF NOT EXISTS idx_human_approval_project_status
ON HumanApprovalQueue(project_id, status);

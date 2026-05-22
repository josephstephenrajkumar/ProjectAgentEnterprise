-- ============================================================
-- Migration 002: Agent Platform Tables
-- Adds AgentConfig, TriggerKeyword, and FlowDefinition tables
-- to support metadata-driven agent configuration and visual
-- flow builder (TO-BE architecture).
-- ============================================================

PRAGMA foreign_keys = ON;

-- ── AgentConfig ─────────────────────────────────────────────
-- Stores agent definitions as database records rather than
-- individual Python files. Enables no-code agent management.

CREATE TABLE IF NOT EXISTS AgentConfig (
    agent_id                TEXT PRIMARY KEY,
    name                    TEXT NOT NULL,
    description             TEXT,
    agent_type              TEXT NOT NULL
                            CHECK (agent_type IN (
                                'chat_responder',
                                'autonomous_workflow',
                                'approval_gated'
                            )),
    system_prompt_template  TEXT NOT NULL,
    tools                   TEXT NOT NULL,     -- JSON array of tool IDs
    tool_execution_order    TEXT,              -- JSON array defining sequence
    autonomy_level          INTEGER NOT NULL DEFAULT 3
                            CHECK (autonomy_level BETWEEN 1 AND 5),
    requires_approval       INTEGER NOT NULL DEFAULT 0,
    output_format           TEXT NOT NULL DEFAULT 'markdown'
                            CHECK (output_format IN ('markdown', 'json', 'table')),
    is_active               INTEGER NOT NULL DEFAULT 1,
    created_by              TEXT DEFAULT 'system',
    created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agent_config_active
ON AgentConfig(is_active, agent_type);

-- ── TriggerKeyword ──────────────────────────────────────────
-- Stores per-agent routing keywords, replacing the hardcoded
-- RULE_KEYWORDS dict in router.py. Keywords can be toggled
-- live without a server restart.

CREATE TABLE IF NOT EXISTS TriggerKeyword (
    keyword_id  TEXT PRIMARY KEY,
    agent_id    TEXT NOT NULL,
    keyword     TEXT NOT NULL,
    match_type  TEXT NOT NULL DEFAULT 'contains'
                CHECK (match_type IN ('contains', 'starts_with', 'exact')),
    priority    INTEGER NOT NULL DEFAULT 10,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(agent_id) REFERENCES AgentConfig(agent_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_trigger_keyword_agent
ON TriggerKeyword(agent_id, is_active, priority);

CREATE UNIQUE INDEX IF NOT EXISTS idx_trigger_keyword_unique
ON TriggerKeyword(agent_id, keyword);

-- ── FlowDefinition ──────────────────────────────────────────
-- Stores user-designed multi-agent workflows as JSON graphs.
-- Used by the visual flow builder canvas in the React UI.
-- The Universal Flow Executor reads this at runtime to build
-- dynamic LangGraph conditional edges.

CREATE TABLE IF NOT EXISTS FlowDefinition (
    flow_id         TEXT PRIMARY KEY,
    flow_name       TEXT NOT NULL,
    description     TEXT,
    trigger_event   TEXT NOT NULL
                    CHECK (trigger_event IN (
                        'forecast_uploaded',
                        'raid_created',
                        'approval_granted',
                        'scheduled',
                        'manual'
                    )),
    flow_graph_json TEXT NOT NULL,  -- JSON: { nodes: [...], edges: [...], conditions: [...] }
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_by      TEXT DEFAULT 'system',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_flow_definition_trigger
ON FlowDefinition(trigger_event, is_active);

-- ── Seed: Migrate existing agents into AgentConfig ──────────
-- Seeds the 8 configurable specialist agents from the current
-- hardcoded Python files into AgentConfig rows.
-- sql_agent, router, synthesizer, general_agent remain as
-- fixed Python nodes (infrastructure concerns, not business agents).

INSERT OR IGNORE INTO AgentConfig
    (agent_id, name, description, agent_type, system_prompt_template,
     tools, tool_execution_order, autonomy_level, requires_approval, output_format)
VALUES

-- Forecast Variance Agent
('forecast_variance_agent',
 'Forecast Variance Agent',
 'Compare Sales baseline, PM initial forecast, previous reforecast, and latest approved forecast to detect financial variance.',
 'chat_responder',
 'You are a financial analyst specializing in project forecasting. Given the following plan versions for a project, write a professional variance report comparing the latest version against the previous version. Highlight revenue delta, cost delta, and gross margin movement. Context: {context}. User asked: {query}',
 '["forecast_version_tool", "summarize_tool"]',
 '["forecast_version_tool", "summarize_tool"]',
 4, 1, 'markdown'),

-- ETC/EAC Metrics Agent
('metrics_agent',
 'ETC/EAC Metrics Agent',
 'Calculate ETC Revenue, ETC Cost, EAC Revenue, EAC Cost, GM Amount, and GM Percent from the ForecastMetricSnapshot table.',
 'chat_responder',
 'You are a financial controller. Present the following project metrics in a clean, structured report. Include ITD, ETC, EAC, and GM figures. Flag any gross margin below 15% as a concern. Context: {context}. User asked: {query}',
 '["metrics_calculator_tool", "summarize_tool"]',
 '["metrics_calculator_tool", "summarize_tool"]',
 4, 0, 'markdown'),

-- Revenue Recognition Agent
('revenue_recognition_agent',
 'Revenue Recognition Agent',
 'Determine whether revenue can be recognized based on achieved hours and milestone completion status.',
 'approval_gated',
 'You are a revenue recognition specialist. Based on the following actuals and milestone data, determine how much revenue can be recognized this period. Apply the recognition rule from PlanRevenueMilestone. Context: {context}. User asked: {query}',
 '["revenue_recognition_tool", "summarize_tool", "approval_gate_tool"]',
 '["revenue_recognition_tool", "summarize_tool", "approval_gate_tool"]',
 4, 1, 'markdown'),

-- RAID Recommendation Agent
('raid_recommendation_agent',
 'RAID Recommendation Agent',
 'Suggest new risks, issues, assumptions, or dependencies based on forecast variance, schedule slippage, and GM deterioration.',
 'approval_gated',
 'You are a proactive Delivery Manager. Review the existing RAID log and the latest project metrics. Suggest 2-3 specific risks or issues that may be missing or underweighted. For each suggestion, provide a description, category, impact area, and recommended mitigating action. Context: {context}. User asked: {query}',
 '["raid_fetch_tool", "metrics_calculator_tool", "summarize_tool", "approval_gate_tool"]',
 '["raid_fetch_tool", "metrics_calculator_tool", "summarize_tool", "approval_gate_tool"]',
 4, 1, 'markdown'),

-- Contract/SOW Agent
('contract_sow_agent',
 'Contract/SOW Agent',
 'Validate milestones, acceptance criteria, obligations, pricing, and commercial clauses using RAG search over uploaded SOW documents.',
 'chat_responder',
 'You are a contract and commercial specialist. Using the following retrieved SOW excerpts, answer the question about contract terms, milestones, obligations, or acceptance criteria. Always cite the work package or clause reference. Context: {context}. User asked: {query}',
 '["rag_search_tool", "summarize_tool"]',
 '["rag_search_tool", "summarize_tool"]',
 3, 0, 'markdown'),

-- Data Quality Agent
('data_quality_agent',
 'Data Quality Agent',
 'Detect missing actuals, stale forecasts, missing milestones, mismatched hours, missing RAID updates, and orphaned plan versions.',
 'approval_gated',
 'You are a data quality auditor. Review the following quality check results for a project. Present findings clearly organized by severity (Critical, Warning, Info). For each issue, explain the business impact and recommended corrective action. Context: {context}. User asked: {query}',
 '["data_quality_tool", "summarize_tool", "approval_gate_tool"]',
 '["data_quality_tool", "summarize_tool", "approval_gate_tool"]',
 4, 1, 'markdown'),

-- MBR Summary Agent
('mbr_summary_agent',
 'MBR Summary Agent',
 'Draft MBR and weekly project summary commentary using metrics, forecast variance, RAID status, and contract findings.',
 'approval_gated',
 'You are a senior Delivery Manager preparing a Monthly Business Review (MBR) summary. Using the financial metrics, open RAID items, and forecast variance data provided, write a professional executive summary. Structure it as: Overall Health, Financial Summary, Key Risks & Issues, Actions Required. Context: {context}. User asked: {query}',
 '["metrics_calculator_tool", "raid_fetch_tool", "forecast_version_tool", "summarize_tool", "approval_gate_tool"]',
 '["metrics_calculator_tool", "raid_fetch_tool", "forecast_version_tool", "summarize_tool", "approval_gate_tool"]',
 4, 1, 'markdown'),

-- Email Agent
('email_agent',
 'Email Agent',
 'Compose and send project status or stakeholder notification emails via the Gmail API integration.',
 'approval_gated',
 'You are a professional business writer. Compose a clear, concise project status email based on the data provided. Keep it under 200 words. Use formal but approachable language. Context: {context}. User asked: {query}',
 '["summarize_tool", "send_email_tool", "approval_gate_tool"]',
 '["summarize_tool", "send_email_tool", "approval_gate_tool"]',
 4, 1, 'markdown');


-- ── Seed: TriggerKeywords for each agent ────────────────────

INSERT OR IGNORE INTO TriggerKeyword (keyword_id, agent_id, keyword, match_type, priority) VALUES
-- Forecast Variance Agent
('tkw_fva_01', 'forecast_variance_agent', 'variance',           'contains', 1),
('tkw_fva_02', 'forecast_variance_agent', 'compare forecast',   'contains', 1),
('tkw_fva_03', 'forecast_variance_agent', 'baseline vs',        'contains', 1),
('tkw_fva_04', 'forecast_variance_agent', 'reforecast',         'contains', 2),

-- Metrics Agent
('tkw_met_01', 'metrics_agent', 'calculate etc',       'contains', 1),
('tkw_met_02', 'metrics_agent', 'calculate eac',       'contains', 1),
('tkw_met_03', 'metrics_agent', 'calculate gm',        'contains', 1),
('tkw_met_04', 'metrics_agent', 'metrics snapshot',    'contains', 1),
('tkw_met_05', 'metrics_agent', 'margin calculation',  'contains', 2),

-- Revenue Recognition Agent
('tkw_rev_01', 'revenue_recognition_agent', 'recognize revenue',    'contains', 1),
('tkw_rev_02', 'revenue_recognition_agent', 'revenue recognition',  'contains', 1),
('tkw_rev_03', 'revenue_recognition_agent', 'milestone met',        'contains', 2),

-- RAID Recommendation Agent
('tkw_rad_01', 'raid_recommendation_agent', 'add a risk',      'contains', 1),
('tkw_rad_02', 'raid_recommendation_agent', 'add an issue',    'contains', 1),
('tkw_rad_03', 'raid_recommendation_agent', 'create risk',     'contains', 1),
('tkw_rad_04', 'raid_recommendation_agent', 'new risk',        'contains', 1),
('tkw_rad_05', 'raid_recommendation_agent', 'create issue',    'contains', 1),
('tkw_rad_06', 'raid_recommendation_agent', 'update raid',     'contains', 2),
('tkw_rad_07', 'raid_recommendation_agent', 'missing po',      'contains', 3),

-- Contract/SOW Agent
('tkw_sow_01', 'contract_sow_agent', 'contract terms',       'contains', 1),
('tkw_sow_02', 'contract_sow_agent', 'sow terms',            'contains', 1),
('tkw_sow_03', 'contract_sow_agent', 'acceptance criteria',  'contains', 1),
('tkw_sow_04', 'contract_sow_agent', 'commercial clause',    'contains', 2),

-- Data Quality Agent
('tkw_dq_01', 'data_quality_agent', 'missing actuals',   'contains', 1),
('tkw_dq_02', 'data_quality_agent', 'data quality',      'contains', 1),
('tkw_dq_03', 'data_quality_agent', 'stale forecast',    'contains', 1),
('tkw_dq_04', 'data_quality_agent', 'orphaned version',  'contains', 2),

-- MBR Summary Agent
('tkw_mbr_01', 'mbr_summary_agent', 'mbr',                      'contains', 1),
('tkw_mbr_02', 'mbr_summary_agent', 'weekly summary',           'contains', 1),
('tkw_mbr_03', 'mbr_summary_agent', 'executive summary',        'contains', 1),
('tkw_mbr_04', 'mbr_summary_agent', 'monthly business review',  'contains', 1),

-- Email Agent
('tkw_eml_01', 'email_agent', 'email',       'contains', 1),
('tkw_eml_02', 'email_agent', 'send email',  'contains', 1),
('tkw_eml_03', 'email_agent', 'mail to',     'contains', 1),
('tkw_eml_04', 'email_agent', 'send to',     'contains', 2);

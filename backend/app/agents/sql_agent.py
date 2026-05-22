"""
SQL Agent — Text-to-SQL Dynamic Agent.

Ported from agents/sql_agent.py. Key improvements:
- Uses centralized settings and LLM factory
- Uses sql_memory_service for template lookup
- Includes the new versioned forecast schema in the schema layer
- Cleaner separation of concerns
"""
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from app.memory.sql_memory_service import lookup_template, record_result, get_semantic_glossary
from app.config.settings import get_settings
from langchain_core.messages import SystemMessage, HumanMessage

import sqlite3
import json

settings = get_settings()
AGENT_NAME = "SQL Inference Agent"

# ── Schema layer ────────────────────────────────────────────────────────────
# The precise representation of all queryable tables.

SCHEMA_LAYER = """
Table: Project
Columns:
- project_id (TEXT, Primary Key)
- ProjectNumber (TEXT, e.g., 'P-123')
- OpportunityID (TEXT)
- customer (TEXT)
- end_customer (TEXT)
- startdateContract (DATETIME)
- endDateContract (DATETIME)
- total_project_cost (FLOAT, Total contractual cost)
- travel_cost (FLOAT)
- other_cost (FLOAT)
- ActiveCurrency (TEXT)
- Proj_Stage (TEXT, e.g. Open/Close)
- Project_Owner (TEXT)
- current_plan_version_id (TEXT, FK to ProjectPlanVersion)
- current_approved_plan_version_id (TEXT, FK to ProjectPlanVersion)

Table: ProjectPlanVersion (Versioned forecasts)
Columns:
- plan_version_id (TEXT, Primary Key)
- project_id (TEXT, FK to Project)
- version_number (INTEGER)
- version_name (TEXT)
- version_type (TEXT, SALES_BASELINE / PM_INITIAL / PM_REFORECAST / SYSTEM_REFORECAST)
- source_type (TEXT, SYSTEM_JSON / EXCEL_UPLOAD / MANUAL / AGENT_DRAFT)
- reporting_month (DATE)
- as_of_date (DATE)
- status (TEXT, Draft / Submitted / Approved / Rejected / Superseded / Locked)
- is_current (INTEGER, 1 = current version)
- is_baseline (INTEGER, 1 = sales baseline)

Table: PlanResource (Resources per plan version)
Columns:
- plan_resource_id (TEXT, Primary Key)
- plan_version_id (TEXT, FK to ProjectPlanVersion)
- role_name (TEXT)
- specialty (TEXT)
- adjusted_rate (REAL)
- cost_per_hour (REAL)
- total_hours (REAL)
- total_fees (REAL)
- total_cost (REAL)

Table: PlanResourceMonth (Monthly resource allocation)
Columns:
- plan_resource_month_id (TEXT, Primary Key)
- plan_resource_id (TEXT, FK to PlanResource)
- month_date (DATE)
- planned_hours (REAL)
- planned_revenue (REAL)
- planned_cost (REAL)

Table: PlanInvoiceMilestone
Columns:
- plan_invoice_id (TEXT, Primary Key)
- plan_version_id (TEXT, FK to ProjectPlanVersion)
- detail (TEXT)
- milestone_date (DATE)
- amount (REAL)
- currency (TEXT)

Table: PlanRevenueMilestone
Columns:
- plan_revenue_id (TEXT, Primary Key)
- plan_version_id (TEXT, FK to ProjectPlanVersion)
- detail (TEXT)
- revenue_date (DATE)
- amount (REAL)
- recognition_rule (TEXT)

Table: PlanMonthlySummary (Aggregated monthly totals per plan version)
Columns:
- plan_monthly_summary_id (TEXT, Primary Key)
- plan_version_id (TEXT, FK to ProjectPlanVersion)
- month_date (DATE)
- total_hours (REAL)
- total_resource_revenue (REAL)
- total_resource_cost (REAL)
- total_invoice_amount (REAL)
- total_month_cost (REAL)

Table: ActualFinancialMonth (Actual financial data by month)
Columns:
- actual_financial_id (TEXT, Primary Key)
- project_id (TEXT, FK to Project)
- month_date (DATE)
- actual_hours (REAL)
- actual_cost (REAL)
- actual_revenue (REAL)
- actual_invoice (REAL)

Table: ForecastMetricSnapshot (ETC/EAC/GM snapshots)
Columns:
- metric_snapshot_id (TEXT, Primary Key)
- project_id (TEXT, FK to Project)
- plan_version_id (TEXT, FK to ProjectPlanVersion)
- reporting_month (DATE)
- itd_revenue (REAL)
- itd_cost (REAL)
- etc_revenue (REAL)
- etc_cost (REAL)
- eac_revenue (REAL)
- eac_cost (REAL)
- gm_amount (REAL)
- gm_percent (REAL)

Table: ProjectWorkPackage
Columns:
- wp_id (TEXT, Primary Key)
- project_id (TEXT, Foreign Key to Project)
- phase_name (TEXT)
- phase_order (INTEGER)
- scope (TEXT)
- deliverables (TEXT)
- activities (TEXT)
- tech_landscape (TEXT)
- quick_summary (TEXT)

Table: RAIDitems
Columns:
- raidID (TEXT, Primary Key)
- project_id (TEXT, Foreign Key to Project)
- LastupdateDate (DATETIME)
- Type (TEXT, e.g. Risk, Issue, Action, Decision)
- Category (TEXT, e.g. High, Medium, Low)
- owner (TEXT)
- Description (TEXT)
- MitigatingAction (TEXT)
- DueDate (DATETIME)
- Status (TEXT, Open, Closed)
- Status_summary (TEXT)
- plan_version_id (TEXT)
- impact_area (TEXT)
- financial_impact (REAL)
- schedule_impact_days (INTEGER)

Table: ProjectWeeklySummary
Columns:
- WeeklyID (TEXT, Primary Key)
- project_id (TEXT, FK)
- date (DATETIME)
- Summary (TEXT)
- overallStatus (TEXT, Green/Amber/Red)
- FinancialPerformance (TEXT)
- Schedule (TEXT)
- plan_version_id (TEXT)
- reporting_month (DATE)

Table: MBRitems
Columns:
- mbr_id (TEXT, Primary Key)
- project_id (TEXT, FK)
- ForecastDateMonth (DATETIME)
- ForecastAmount (FLOAT)
- Status (TEXT)
- plan_version_id (TEXT)

Table: ProjectMonthlyHours (Time-phased metrics)
Columns:
- entry_id (TEXT, Primary Key)
- project_id (TEXT, Foreign Key to Project)
- date (DATETIME)
- hours (FLOAT)
- cost (FLOAT)
- revenue (FLOAT)

Table: SemanticMap (Glossary)
Columns:
- keyword (TEXT, e.g. 'overdue', 'high priority')
- entity (TEXT, e.g. 'RAIDitems')
- attribute (TEXT, e.g. 'DueDate')
- filter_logic (TEXT, e.g. 'DueDate < date()')
"""


def _get_generation_prompt(glossary: str, pattern_hint: str = "", project_id: str = None, project_number: str = None) -> str:
    context_str = ""
    filter_rule = ""
    if project_id or project_number:
        context_str = f"\nThe current query context is for the project with Project ID: '{project_id or ''}' and Project Number: '{project_number or ''}'.\n"
        filter_rule = f"\n2. ALWAYS filter your query by the current project context. Use `project_id = '{project_id}'` or `ProjectNumber LIKE '%{project_number}%'` where applicable to ensure you only return data for this specific project."
    else:
        filter_rule = "\n2. Filter your query by the project context if specified in the user's question."

    return f"""
You are an expert SQLite Database Administrator.
You have access to the following SQLite database schema:

{SCHEMA_LAYER}
{glossary}
{context_str}
Your task is to generate a dynamic SQL query to answer the user's question.

CRITICAL RULES:
1. ONLY USE COLUMNS LISTED IN THE SCHEMA ABOVE.{filter_rule}
3. NEVER USE 'subtotal', 'total_contract_value', 'currency', 'status' (use Proj_Stage), or 'Priority' (use Category). These are DEPRECATED.
4. Use 'total_project_cost' for project financials.
5. Use 'ActiveCurrency' instead of 'currency'.
6. AVOID FAN-OUT: Never join the Project table to multiple one-to-many tables in a single query when calculating SUM or COUNT.
7. STRING COMPARISON: Always use `LIKE '%term%'` instead of `=` for customer names or project numbers.
8. DO NOT interpret project numbers as years. Do NOT add `strftime('%Y', ...)` filters unless the user explicitly mentions a year.
9. DO NOT output markdown blocks. Output ONLY the raw SQL string or the word FALLBACK.
10. For forecast questions, join through ProjectPlanVersion using is_current=1 for the latest version.
11. For ETC/EAC/GM, use ForecastMetricSnapshot if available.
{pattern_hint}
"""


SYNTHESIS_PROMPT = """
You are a Project Intelligence Analyst.
Write a professional response based ONLY on these database results.

User Question: {query}
SQL Executed: {sql}
Results (JSON): {results}
"""


def sql_agent_node(state: AgentState) -> dict:
    """Text-to-SQL agent: first responder for all queries."""
    query = state["query"]
    current_outputs = state.get("agent_outputs", [])
    debug = state.get("debug_log", "")
    llm = get_llm()

    project_id = state.get("project_id")
    project_number = state.get("project_number") or state.get("project_code")

    # Retrieve ProjectNumber from SQLite if we only have project_id
    if project_id and not project_number:
        try:
            conn = sqlite3.connect(settings.db_abs_path)
            row = conn.execute("SELECT ProjectNumber FROM Project WHERE project_id = ?", (project_id,)).fetchone()
            if row:
                project_number = row[0]
            conn.close()
        except Exception:
            pass

    # 1. Check SQL memory for cached templates
    glossary = get_semantic_glossary()
    pattern_hint = ""
    cache_hit = lookup_template(query)
    if cache_hit:
        debug += f"\n🧠 {AGENT_NAME}: Found cached pattern (confidence: {cache_hit['confidence_score']:.2f})"
        pattern_hint = (
            f"\nSUCCESSFUL PATTERN (Reference only):\n"
            f"Past Query: {cache_hit.get('past_query', cache_hit['intent_name'])}\n"
            f"Past SQL: {cache_hit['sql_template']}\n"
        )

    # 2. Generate SQL via LLM
    history = state.get("history", [])
    sanitized_history = history[-6:]
    messages = [SystemMessage(content=_get_generation_prompt(glossary, pattern_hint, project_id, project_number))]
    for msg in sanitized_history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=f"PAST QUERY: {msg['content']}"))
        else:
            messages.append(SystemMessage(content="PAST RESPONSE: [Data provided based on past schema]"))

    messages.append(HumanMessage(content=f"Current Objective: {query}"))

    try:
        sql_response = llm.invoke(messages)
        generated_sql = sql_response.content.strip()

        # Strip markdown fences
        if "```" in generated_sql:
            generated_sql = generated_sql.split("```")[-2].split("\n", 1)[-1].strip()

    except Exception as e:
        debug += f"\n⚠️ {AGENT_NAME}: LLM SQL generation failed: {e}."
        generated_sql = "FALLBACK"

    if generated_sql == "FALLBACK" or not generated_sql.upper().startswith("SELECT"):
        return {
            "next_node": "router",
            "debug_log": debug + f"\n🔄 {AGENT_NAME}: Question cannot be answered via DB. Triggering RAG fallback.",
        }

    debug += f"\n🔍 {AGENT_NAME} generated SQL:\n{generated_sql}"

    # 3. Execute SQL
    results = []
    try:
        conn = sqlite3.connect(settings.db_abs_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Prepare parameter bindings in case the LLM generated named parameters
        bindings = {}
        if project_id:
            bindings["project_id"] = project_id
        if project_number:
            bindings["project_code"] = project_number
            bindings["project_number"] = project_number

        cursor.execute(generated_sql, bindings)
        rows = cursor.fetchall()
        for r in rows:
            results.append(dict(r))
        conn.close()
    except Exception as e:
        debug += f"\n❌ {AGENT_NAME}: SQL Execution failed: {e}. Falling back."
        record_result(query, generated_sql, -1)
        return {
            "next_node": "router",
            "debug_log": debug,
            "agent_outputs": current_outputs + [
                f"*(SQL Agent attempted query but failed: {e}. Falling back to document search.)*"
            ],
        }

    # 4. Handle empty results
    if not results:
        debug += f"\n⚠️ {AGENT_NAME}: SQL returned 0 results. Triggering RAG fallback."
        return {
            "next_node": "router",
            "debug_log": debug,
            "agent_outputs": current_outputs + [
                f"*(SQL Agent executed: `{generated_sql}` but found 0 matching records. Falling back to document search.)*"
            ],
        }

    # Record success
    record_result(query, generated_sql, 1)

    # 5. Synthesize results
    formatted_results = json.dumps(results, indent=2)
    final_prompt = SYNTHESIS_PROMPT.format(query=query, sql=generated_sql, results=formatted_results)

    try:
        final_response = llm.invoke([HumanMessage(content=final_prompt)])
        report = final_response.content.strip()
    except Exception as e:
        report = f"Failed to synthesize SQL results: {e}"

    full_report = (
        f"--- 🗄️ {AGENT_NAME} Report ---\n{report}\n\n"
        f"**Executed SQL Query:**\n```sql\n{generated_sql}\n```\n"
    )

    return {
        "response": report,
        "agent_outputs": current_outputs + [full_report],
        "debug_log": debug + f"\n✅ {AGENT_NAME}: Successfully answered from database.",
        "next_node": "END",
        "last_sql_intent": query,
        "sql_result": results,
    }

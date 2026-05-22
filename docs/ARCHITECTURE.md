# Detailed Design & Architecture: ProjectAgentEnterprise

This document provides a comprehensive view of the architectural design, agent routing workflows, document extraction systems, and operational governance rules in **ProjectAgentEnterprise**.

---

## 1. Evolution from OpenClaw

The system transitioned from a command-line/notebook prototype using the legacy **OpenClaw** framework into an enterprise-ready web application:

| Architectural Component | Legacy OpenClaw Prototype | Refactored Enterprise Architecture |
| :--- | :--- | :--- |
| **Frontend** | Vanilla HTML / CSS / JS with socket wrappers | **React.js** with TypeScript, Tailwind CSS, and Vite |
| **Backend Gateway** | Node.js gateway (running port 3000) | **FastAPI** REST API on port 8000 |
| **Orchestration** | Python FastAPI with in-memory dicts | **LangGraph StateGraph** with file-backed session memory |
| **Agent Registry** | Custom A2A card declarations | Centralized **YAML configuration files** |
| **Database** | Normalized SQLite tables only | Relational version-controlled planning schema |
| **Document Search** | Single-pass vector similarity (k=30 limit) | **Map-Reduce Discovery + Targeted Retrieval** |
| **Governance** | Direct edits or basic console outputs | **Human-in-the-Loop approval queue** with audit logs |

---

## 2. Multi-Agent Orchestration (LangGraph)

The core logic of the chat console runs on **LangGraph**. The system leverages a **Supervisor-Agent** pattern.

### 2.1 The Complete StateGraph Flow
The compiled StateGraph workflow maps any user query from the entry node through the routing gates to the correct specialist agents, supporting concurrent execution ("fanning out") and synthesis:

```mermaid
graph TD
    %% Define Styles
    classDef startEnd fill:#2ecc71,stroke:#27ae60,stroke-width:2px,color:#fff;
    classDef entry fill:#3498db,stroke:#2980b9,stroke-width:2px,color:#fff;
    classDef decision fill:#f1c40f,stroke:#f39c12,stroke-width:2px,color:#333;
    classDef specialist fill:#9b59b6,stroke:#8e44ad,stroke-width:2px,color:#fff;
    classDef helper fill:#e67e22,stroke:#d35400,stroke-width:2px,color:#fff;

    %% Define Nodes
    START([● START]):::startEnd
    SQL[sql_agent]:::entry
    SQL_DECISION{sql_decision?}:::decision
    ROUTER[router]:::entry
    ROUTE_DECISION{route_decision?}:::decision
    SYNTH[synthesizer]:::helper
    END([■ END]):::startEnd

    %% Specialist Nodes
    RAG[rag_agent]:::specialist
    FORECAST[forecast_agent]:::specialist
    CONTRACT[contract_agent]:::specialist
    VARIANCE[forecast_variance_agent]:::specialist
    METRICS[metrics_agent]:::specialist
    REV_REC[revenue_recognition_agent]:::specialist
    RAID_REC[raid_recommendation_agent]:::specialist
    RISK[risk_agent]:::specialist
    SOW[contract_sow_agent]:::specialist
    DQ[data_quality_agent]:::specialist
    MBR[mbr_summary_agent]:::specialist
    DEL[delete_agent]:::specialist
    EMAIL[email_agent]:::specialist
    GEN[general_agent]:::specialist

    %% Graph Structure Flow
    START --> SQL
    SQL --> SQL_DECISION

    %% SQL Conditional Gate
    SQL_DECISION -- "1. Query Resolved" --> END
    SQL_DECISION -- "2. Needs Fallback" --> ROUTER

    %% Router Conditional Gate
    ROUTER --> ROUTE_DECISION

    %% Fanned Out / Combined Route (both)
    ROUTE_DECISION -- "Route: 'both'" --> FORECAST & CONTRACT
    FORECAST --> SYNTH
    CONTRACT --> SYNTH
    SYNTH --> END

    %% Specialist Direct-to-END Routes
    ROUTE_DECISION -- "Route: 'rag_agent'" --> RAG
    ROUTE_DECISION -- "Route: 'forecast_variance_agent'" --> VARIANCE
    ROUTE_DECISION -- "Route: 'metrics_agent'" --> METRICS
    ROUTE_DECISION -- "Route: 'revenue_recognition_agent'" --> REV_REC
    ROUTE_DECISION -- "Route: 'raid_recommendation_agent'" --> RAID_REC
    ROUTE_DECISION -- "Route: 'risk_agent'" --> RISK
    ROUTE_DECISION -- "Route: 'contract_sow_agent'" --> SOW
    ROUTE_DECISION -- "Route: 'data_quality_agent'" --> DQ
    ROUTE_DECISION -- "Route: 'mbr_summary_agent'" --> MBR
    ROUTE_DECISION -- "Route: 'delete_agent'" --> DEL
    ROUTE_DECISION -- "Route: 'email_agent'" --> EMAIL
    ROUTE_DECISION -- "Route: 'general_agent'" --> GEN

    %% Direct Edges to END
    RAG & VARIANCE & METRICS & REV_REC & RAID_REC & RISK & SOW & DQ & MBR & DEL & EMAIL & GEN --> END
```

### 2.2 Lifecycle Sequence of a User Query
This diagram tracks a query from the frontend, through API validation and LangGraph execution, down to the database layers:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / PM
    participant UI as React Chat Console
    participant API as FastAPI Backend (api/chat)
    participant Graph as LangGraph Orchestrator
    participant SQL as SQL Agent
    participant Router as Supervisor Router
    participant Spec as Specialist Agent(s)
    participant Synth as Synthesizer
    participant DB as SQLite / ChromaDB

    User->>UI: Types query & clicks "Send"
    UI->>API: POST /api/chat { query, session_id }
    Note over API: Load session history & retrieve memory
    API->>Graph: chat_graph.invoke(initial_state)

    Graph->>SQL: Invoke sql_agent_node(state)
    SQL->>DB: Check template & run query (read-only)
    DB-->>SQL: Query results

    alt SQL Agent succeeds & answers query
        SQL->>Graph: Returns answered state (next_node = 'END')
    else SQL Agent fails / needs unstructured data
        SQL->>Graph: Returns fallback state (next_node = 'router')
        Graph->>Router: Invoke router_node(state)
        Router-->>Graph: Returns routing decision (next_node)
        
        alt Single Specialist Route (e.g. RAG)
            Graph->>Spec: Invoke rag_agent_node(state)
            Spec->>DB: Fetch context from ChromaDB
            DB-->>Spec: Text segments / citations
            Spec->>Graph: Returns response state
        else Fanned-out Multi-Agent Route (e.g. 'both')
            par Run Forecast Agent
                Graph->>Spec: Invoke forecast_agent_node(state)
            and Run Contract Agent
                Graph->>Spec: Invoke contract_agent_node(state)
            end
            Graph->>Synth: Invoke synthesizer_node(state)
            Synth->>Graph: Returns fanned-in response state
        end
    end

    Graph-->>API: Compiled final state
    API-->>UI: JSON { response, debug_log }
    UI->>User: Displays answer & agent trace logs
```

### 2.3 Hybrid Intent Routing
The Supervisor Router routes queries using a three-layer priority system:
1. **Deterministic Rule Matching**: Identifies core keywords to map queries immediately to specific agents (e.g. `"etc"`, `"eac"`, or `"gm"` bypass LLM classification and route directly to the SQL agent).
2. **SQL Glossary Memory Lookup**: Matches query patterns against `SqlQueryMemory` to check if a high-confidence query pattern exists.
3. **LLM Classification Fallback**: Invokes the LLM to classify ambiguous queries into one of the specialist agent identifiers (or `"both"`/`"general"`).

---

## 3. SQL Translation & Dynamic Generation Layer

The **SQL Inference Agent** utilizes a Text-to-SQL dynamic pipeline to translate natural language user questions into read-only SQL statements. The process uses query caching, glossary mapping, strict safety rules, and validation scoring.

### 3.1 Text-to-SQL Process Flow Diagram

```mermaid
graph TD
    UserQuery([User Input Query]) --> LookupCache[1. Lookup SqlQueryMemory for cached patterns]
    LookupCache --> CheckCache{Cache Hit & Confidence > 0.8?}
    
    CheckCache -- Yes --> UseTemplate[2. Retrieve template & set Pattern Hint]
    CheckCache -- No --> SetEmptyHint[Set Empty Pattern Hint]
    
    UseTemplate --> BuildPrompt[3. Build prompt: Schema + Glossary + Constraints + Pattern Hint]
    SetEmptyHint --> BuildPrompt
    
    BuildPrompt --> CallLLM[4. Call LLM Groq with Chat History]
    CallLLM --> CheckFallback{Generated Output is 'FALLBACK' or not a SELECT?}
    
    CheckFallback -- Yes --> RAGRoute((Trigger RAG Fallback))
    CheckFallback -- No --> ParseSQL[5. Parse & Strip markdown fences to extract raw SQL]
    
    ParseSQL --> ExecuteSQL[6. Execute raw SQL query against SQLite]
    ExecuteSQL --> CheckResult{Execution Successful & Returns Rows?}
    
    CheckResult -- No (Error or 0 rows) --> UpdateCacheFail[7a. Record score -1 in SqlQueryMemory]
    UpdateCacheFail --> RAGRoute
    
    CheckResult -- Yes --> UpdateCacheSuccess[7b. Record score +1 in SqlQueryMemory]
    UpdateCacheSuccess --> Synthesize[8. Send JSON results + Query to LLM for report synthesis]
    Synthesize --> RenderOutput([Render Markdown Answer in Chat Console])
```

### 3.2 SQL Generation and Execution Details

#### A. Session Memory & Glossary Loading
The agent retrieves context data (e.g. current project, active forecast cycle) from the `AgentState` short-term memory keys (`project_id`, `reporting_month`). Simultaneously, it queries the `SemanticMap` glossary table to load user-customized keyword mappings, such as mapping the term `"overdue"` to the specific SQL filter `"DueDate < date('now')"`.

#### B. Prompt Formulation & Safety Constraints
A detailed prompt is sent to the LLM containing the schema definitions, glossary keywords, and strict negative constraints:
* **No Deprecated Columns**: The prompt explicitly forbids the use of columns that are no longer part of the relational schema (such as `subtotal`, `Priority`, and `currency`).
* **Prevent Fan-out Aggregations**: Instructs the LLM not to join the main `Project` table to multiple one-to-many tables (like joining both `ProjectWorkPackage` and `RAIDitems` in a single query) because doing so corrupts mathematical summaries (`SUM`, `COUNT`).
* **String Comparison Safeguard**: Enforces `LIKE '%term%'` instead of `=` for text fields to accommodate formatting variance.
* **No Date Conversions for IDs**: Prevents the LLM from trying to convert project numbers (e.g., `202021`) into year filters.

#### C. Verification, Scoring, and Feedback Loop
When the LLM outputs a SQL query, it is executed inside a validation wrapper:
* **Success Gate**: If the query executes successfully and returns rows, the pattern is cached or incremented in `SqlQueryMemory` via `record_result(query, generated_sql, 1)`.
* **Failure Gate**: If the query generates an SQLite syntax error, contains forbidden commands (non-SELECT writes), or returns `0` records, it is logged and down-scored via `record_result(query, generated_sql, -1)`. The system then updates the state to fallback to the `router` node to invoke unstructured document search (RAG).

#### D. Synthesis
The returned query dataset is serialized into a JSON array and sent to the LLM. The LLM acts as a financial analyst, converting the raw data tables into a concise, professional markdown response.

---

## 4. SOW Extraction Strategy (Map-Reduce + Targeted Retrieval)

The previous system suffered from silent extraction failures. When processing a 100+ page SOW contract using basic vector similarity retrieval (e.g. `k=30`), similar chunks pushed crucial work package milestones out of the LLM context window.

To guarantee 100% extraction coverage, the system uses a **Map-Reduce Discovery** and **Targeted Retrieval** pipeline:

```text
SOW Document
   ↓
Pass 1: Map-Reduce Discovery
  ├── 1. Read all document nodes from ChromaDB
  ├── 2. Pre-filter nodes matching terms: "work package", "phase", "appendix"
  ├── 3. Send chunks to LLM: "Identify any work package phase names and numbers"
  └── 4. Reduce: Deduplicate, sort sequentially, and construct WorkPackage list
   ↓
Pass 2: Targeted Detail Retrieval
  ├── For each discovered Work Package (e.g. WP 5):
  │     ├── Run vector query: "WP 5 scope deliverables activities milestones"
  │     └── Send top 10 relevant nodes + WP details to LLM for full extraction
  └── Validate output strictly using Pydantic JSON schemas
   ↓
Save to ProjectWorkPackage Table (ON DELETE CASCADE active)
```

This guarantees that:
* **Context Contamination is Eliminated**: Chunks from other phases are excluded during details extraction.
* **Strict Validation**: Langchain's `PydanticOutputParser` verifies that all 15 required fields are returned in JSON.

---

## 5. Human-in-the-Loop Governance Model

To prevent autonomous agents from accidentally editing project budgets, financial actuals, or contracts, the system enforces a strict **Level 3-4 Autonomy Model**:

* **What Agents Can Do Independently**:
  * Analyze trends and calculate budget variance (ETC/EAC).
  * Flag project risks and recommend new RAID items.
  * Audit data quality (empty fields, layout schema mismatches).
  * Generate draft Monthly Business Review (MBR) reports.
* **What Agents CANNOT Do Independently (Approval Required)**:
  * Overwrite financial actual records.
  * Formally approve forecast plan versions.
  * Add live RAID items to the active ledger.
  * Dispatch emails or release reports to stakeholders.

### 5.1 Approval Workflow
1. When an agent determines a change is necessary, it creates a record in `AgentActionLog` with `requires_human_approval = 1`.
2. It pushes the action payload to the `HumanApprovalQueue` in a `Pending` state.
3. The React Frontend alerts the user in the **Approval Queue** dashboard.
4. If approved, the service executes the proposed action and updates status to `Approved`. If rejected, it records the rejection comments and status remains `Rejected`.

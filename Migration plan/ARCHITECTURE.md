# ProjectAgentEnterprise Refactor Architecture

## Objective

Refactor `https://github.com/josephstephenrajkumar/ProjectAgentEnterprise` from an OpenClaw-based multi-agent prototype into an enterprise-ready agentic AI system using:

- React frontend
- FastAPI backend
- Python service layer
- LangGraph agent orchestration
- LlamaIndex for document ingestion, semantic chunking, metadata-aware retrieval
- SQLite initially, with Postgres-ready design
- ChromaDB initially, with pgvector/OpenSearch-ready design
- Human-in-the-loop approval for financial and governance actions

## Current Repo Baseline

Current repository structure observed from GitHub README:

```text
openclaw-multiagent/
├── ui/                      # Chat UI HTML/CSS/JS
├── runtime/                 # OpenClaw Node.js runtime/gateway
├── orchestrator/            # Python FastAPI + LangGraph
├── agents/                  # forecast, contract, general, synthesizer
├── tools/                   # ingestion/retrieval tools
├── data/docs/               # source documents
├── data/chroma_db/          # vector database
└── requirements.txt
```

## Target Architecture

```text
React Frontend
  ├── Project Forecast Dashboard
  ├── Forecast Upload
  ├── Forecast Version History
  ├── Forecast Comparison
  ├── RAID Impact View
  ├── Weekly / MBR Summary
  ├── Agent Review / Approval Queue
  └── Chat / Agent Console

FastAPI Backend
  ├── REST API Gateway
  ├── Project Service
  ├── Forecast Version Service
  ├── Forecast Upload Service
  ├── Actuals Service
  ├── Metrics Service
  ├── Revenue Recognition Service
  ├── RAID Service
  ├── Summary Service
  ├── SQL Memory Service
  ├── LlamaIndex Ingestion Service
  └── LangGraph Agent Orchestrator

LangGraph Agent Layer
  ├── Supervisor Router Agent
  ├── SQL Agent
  ├── RAG Agent
  ├── Forecast Variance Agent
  ├── ETC/EAC Metrics Agent
  ├── Revenue Recognition Agent
  ├── RAID Recommendation Agent
  ├── Contract/SOW Agent
  ├── Data Quality Agent
  └── MBR Summary Agent
```

## Core Refactor Principle

Remove OpenClaw runtime as the core framework.

Preserve the useful concepts:
- Agent cards
- A2A-style agent capability registry
- ACP-style message envelope
- Agent mesh
- Tool invocation
- Router
- SQL/RAG split
- Short-term and long-term memory

Reimplement them using:
- FastAPI
- Pydantic
- LangGraph
- Python service classes
- YAML agent registry
- LlamaIndex tools

## Runtime Flow

### User chat query

```text
React Chat UI
→ POST /api/chat
→ FastAPI Chat Controller
→ LangGraph Supervisor Router
→ Rule/Embedding/LLM Hybrid Intent Router
    ├── SQL Agent
    ├── LlamaIndex RAG Agent
    ├── Forecast Agent
    ├── RAID Agent
    └── Summary Agent
→ Synthesizer
→ Response + trace/debug metadata
```

### Forecast upload event

```text
PM uploads forecast Excel
→ FastAPI Forecast Upload Service
→ Create ProjectPlanVersion
→ Parse forecast rows
→ Rebuild PlanMonthlySummary
→ Emit internal event: forecast_uploaded
→ LangGraph autonomous workflow
    ├── Forecast Variance Agent
    ├── ETC/EAC Metrics Agent
    ├── Revenue Recognition Agent
    ├── RAID Recommendation Agent
    └── MBR Summary Agent
→ Draft recommendations
→ Human approval queue
```

## Autonomy Model

Recommended autonomy level: Level 3-4.

Agents can:
- auto-analyze
- auto-calculate
- auto-detect variance
- auto-suggest RAID
- auto-draft summaries
- auto-create draft recommendations

Agents must not directly:
- approve forecasts
- change financial actuals
- finalize RAID records
- publish final MBR reports

Human approval required for:
- financial record changes
- approved forecast version
- RAID creation
- external communication
- MBR publication

## LlamaIndex Integration

Use LlamaIndex to replace manual chunking and retrieval logic.

Recommended pipeline:

```text
File Upload
→ LlamaIndex Reader / Unstructured
→ SemanticSplitterNodeParser
→ Metadata enrichment
→ Vector index
→ Metadata-filtered retrieval
→ RAG Agent response
```

Metadata to attach:
- project_id
- document_id
- document_type
- sow_id
- work_package_id
- source_file_name
- page_number / sheet_name
- effective_date
- customer
- contract_version

## SQL vs RAG Routing

Use hybrid routing:

1. Deterministic rules for obvious finance/project terms
2. Embedding-based intent matching
3. LLM fallback classifier only for ambiguous queries
4. Mixed query routing when both SQL and RAG are needed

## Learning Layer

Retain and improve the existing QueryFeedback/SemanticMap logic.

```text
User query
→ Normalize query
→ Use short-term memory for project/month/version context
→ Lookup SqlQueryMemory and QueryFeedback
→ If high-confidence SQL template exists, reuse it
→ Else generate SQL
→ SQL safety validation
→ Execute read-only query
→ User/agent feedback updates query memory
```

## A2A / ACP Migration

| OpenClaw Concept | New Architecture |
|---|---|
| A2A Card | agent_registry.yaml |
| ACP Server | FastAPI Agent Gateway |
| ACP Message | Pydantic AgentRequest / AgentResponse |
| Skills | LangGraph tools + Python services |
| Agent mesh | LangGraph nodes and conditional edges |
| Agent discovery | YAML registry + service registry |

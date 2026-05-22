# ProjectAgentEnterprise: Multi-Agent Financial Management System

A production-ready, locally-runnable multi-agent AI system designed for project financial planning, forecast versioning, and operational governance. The architecture features a modern **React/Vite** frontend and a **FastAPI/LangGraph** backend with a relational plan versioning schema.

---

## Architecture Overview

```text
React Frontend (frontend-react/)
       ↓ (REST API on port 8000)
FastAPI Backend (backend/app/main.py)
       ↓ (Service Layer / SQLite)
LangGraph Supervisor Orchestrator (backend/app/graph/supervisor_graph.py)
       ↓
Agent Mesh (backend/app/agents/)
 ├── Supervisor Router Agent  ├── Forecast Variance Agent
 ├── SQL Agent                ├── ETC/EAC Metrics Agent
 ├── RAG Agent                ├── Revenue Recognition Agent
 ├── Contract/SOW Agent       ├── RAID Recommendation Agent
 ├── Data Quality Agent       └── MBR Summary Agent
```

---

## Quick Start & Installation

### 1. Prerequisites
* **Python 3.10+** (WSL/Ubuntu environment recommended)
* **Node.js 18+** & **npm**
* A [Groq Cloud Account](https://console.groq.com) and an API key.

### 2. Configure Environment Variables
Copy `.env.example` in the root folder to `.env` and fill in your credentials:
```bash
cd /home/joseph/ProjectAgentEnterprise
cp .env.example .env
```
Ensure `.env` contains:
```env
GROQ_API_KEY="your-groq-api-key"
SQLITE_DB_PATH="./data/openclaw.db"
CHROMA_DB_PATH="./data/chroma_db"
EMBEDDING_MODEL="all-mpnet-base-v2"
```

### 3. Initialize the SQLite Database
If the SQLite database does not exist or needs to be reinitialized, run the setup script:
```bash
python tools/init_sqlite_db.py
```
*Note: This creates the baseline tables. The backend will automatically apply migrations (`ProjectPlanVersion`, etc.) on startup.*

---

### 4. Running the Backend Server
1. Navigate to the project root directory:
   ```bash
   cd /home/joseph/ProjectAgentEnterprise
   ```
2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Start the FastAPI backend via Uvicorn:
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   *The server runs at **http://localhost:8000**.*

---

### 5. Running the React Frontend
1. Open a new terminal session and navigate to the frontend directory:
   ```bash
   cd /home/joseph/ProjectAgentEnterprise/frontend-react
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The interface runs at **http://localhost:5173** (or the URL output in your terminal).*

---

## Project Directory Structure

```text
ProjectAgentEnterprise/
├── backend/
│   ├── app/
│   │   ├── api/             # REST controllers (chat, forecast, agents)
│   │   ├── agents/          # LangGraph agent definitions and templates
│   │   ├── config/          # Settings configurations (.env loader)
│   │   ├── db/              # SQLite SQLAlchemy engine and session makers
│   │   ├── graph/           # LangGraph supervisor workflow definition
│   │   ├── memory/          # Persistent conversation and session storage
│   │   ├── rag/             # Document retrieval handlers (ChromaDB)
│   │   ├── services/        # Business logic services (approvals, metrics)
│   │   └── main.py          # FastAPI application entrypoint
│   ├── migrations/          # SQLite schema SQL migration definitions
│   └── requirements.txt     # Backend python dependencies
│
├── frontend-react/
│   ├── src/
│   │   ├── components/      # Common components (Layout, Navigation)
│   │   ├── pages/           # Pages (Dashboard, ChatConsole, DataManager)
│   │   ├── App.tsx          # Main React routes
│   │   └── main.tsx         # React DOM renderer
│   ├── package.json         # Node scripts & packages
│   └── vite.config.ts       # Vite config
│
├── data/                    # SQLite database and ChromaDB vector files
├── docs/                    # Architectural and operational documentation
└── tools/                   # Database setup and script utilities
```

---

## API Documentation

The FastAPI backend exposes the following endpoint routing routes on port `8000`:

### 1. Chat Console Interface
* **`POST /api/chat`**
  * **Payload**: `{"query": "...", "session_id": "..."}`
  * **Response**: `{"response": "...", "route": "...", "debug_log": "..."}`
  * Routes queries through the LangGraph supervisor router to generate SQL or fetch RAG context.

### 2. Project Financial Forecasting
* **`GET /api/forecast/versions/{project_id}`**
  * Fetches the plan version history for a project.
* **`POST /api/forecast/upload`**
  * Uploads an Excel forecast spreadsheet to draft/submit a new plan version.
* **`POST /api/forecast/approve/{plan_version_id}`**
  * Formally approves a plan version, making it the active baseline.

### 3. Agent Performance and Metrics
* **`GET /api/agents`**
  * Retrieves list of registered agent capabilities.
* **`GET /api/agents/approval-queue`**
  * Lists outstanding tasks in the Human-in-the-Loop approval queue.
* **`POST /api/agents/approve-action/{approval_id}`**
  * Authorizes or rejects a proposed agentic edit.

"""
FastAPI application entry point.

Replaces orchestrator/main.py. No OpenClaw runtime dependency.
React frontend calls this directly.
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings
from app.api.chat import router as chat_router
from app.api.forecast import router as forecast_router
from app.api.agents import router as agents_router

settings = get_settings()


# ── Lifespan: run migrations on startup ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run database migrations and schema setup on startup."""
    _run_migrations()
    yield


def _run_migrations():
    """Apply the versioned financial forecast schema on startup."""
    from app.db.engine import get_raw_connection

    migration_path = os.path.join(
        os.path.dirname(__file__), "..", "migrations",
        "001_agentic_financial_forecast_schema.sql",
    )
    if os.path.exists(migration_path):
        conn = get_raw_connection()
        try:
            with open(migration_path, "r") as f:
                conn.executescript(f.read())
            conn.commit()
            print("✅ Migration 001 applied successfully.")
        except Exception as e:
            print(f"⚠️ Migration 001 warning: {e}")
        finally:
            conn.close()
    else:
        print(f"⚠️ Migration file not found: {migration_path}")


# ── App factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="ProjectAgentEnterprise",
        description=(
            "Enterprise-grade multi-agent AI system for project financial management. "
            "React Frontend → FastAPI → LangGraph → SQL/RAG/Specialist Agents."
        ),
        version="4.0.0",
        lifespan=lifespan,
    )

    # CORS
    origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(chat_router)
    app.include_router(forecast_router)
    app.include_router(agents_router)

    # ── Health ──────────────────────────────────────────────────────────────

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "project-agent-enterprise", "version": "4.0.0"}

    return app


app = create_app()


# ── CLI entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )

"""
Database engine and session management.

Key design decisions:
- Uses SQLAlchemy for ORM abstraction (Postgres-ready).
- Enables WAL mode and foreign keys on every connection for SQLite concurrency.
- Provides a dependency-injectable `get_db` generator for FastAPI routes.
"""
import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from app.config.settings import get_settings

settings = get_settings()


# ── SQLAlchemy engine ───────────────────────────────────────────────────────

_db_url = f"sqlite:///{settings.db_abs_path}"

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False},
    echo=False,
)


# ── SQLite PRAGMA enforcement ───────────────────────────────────────────────
# These fire on every new raw connection to ensure WAL + FK constraints.

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base for ORM models ────────────────────────────────────────

Base = declarative_base()


# ── FastAPI dependency ──────────────────────────────────────────────────────

def get_db():
    """Yield a SQLAlchemy session; auto-close on request completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Raw connection helper (for migration scripts) ──────────────────────────

def get_raw_connection() -> sqlite3.Connection:
    """Return a raw sqlite3 connection with WAL + FK enabled.
    Used for migration scripts and the migration_loader."""
    conn = sqlite3.connect(settings.db_abs_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

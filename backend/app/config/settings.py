"""
Centralized application settings.
Loads from .env and provides typed access via Pydantic BaseSettings.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    # ── LLM / Groq ─────────────────────────────────────────────────────────
    groq_api_key: str = ""
    llm_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.3

    # ── Database ────────────────────────────────────────────────────────────
    sqlite_db_path: str = "./data/openclaw.db"

    # ── Vector Store ────────────────────────────────────────────────────────
    chroma_db_path: str = "./data/chroma_db"
    embedding_model: str = "all-mpnet-base-v2"

    # ── Server ──────────────────────────────────────────────────────────────
    host: str = "localhost"
    port: int = 8000
    cors_origins: str = "*"

    # ── Data ────────────────────────────────────────────────────────────────
    source_data_dir: str = "./data/docs"
    projects_dir: str = "./data/docs/projects"

    model_config = {
        "env_file": os.path.join(
            os.path.dirname(__file__), "..", "..", "..", ".env"
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def db_abs_path(self) -> str:
        """Resolve the SQLite path relative to the project root."""
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        if os.path.isabs(self.sqlite_db_path):
            return self.sqlite_db_path
        return os.path.abspath(os.path.join(project_root, self.sqlite_db_path))

    @property
    def chroma_abs_path(self) -> str:
        """Resolve the ChromaDB path relative to the project root."""
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..")
        )
        if os.path.isabs(self.chroma_db_path):
            return self.chroma_db_path
        return os.path.abspath(os.path.join(project_root, self.chroma_db_path))


@lru_cache()
def get_settings() -> Settings:
    return Settings()

"""
LLM factory: returns a Groq-hosted LLM.
Centralized so model/temperature changes are applied globally.
"""
from functools import lru_cache
from app.config.settings import get_settings


@lru_cache()
def get_llm():
    from langchain_groq import ChatGroq

    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in .env")

    return ChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )

"""
LLM factory: returns a Groq-hosted LLM.
Centralized so model/temperature changes are applied globally.
"""
from functools import lru_cache
from app.config.settings import get_settings


@lru_cache()
def get_llm():
    import os
    from langchain_groq import ChatGroq

    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not set in .env")

    # Set environment variable so underlying SDKs can read it if needed
    os.environ["GROQ_API_KEY"] = settings.groq_api_key

    return ChatGroq(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        api_key=settings.groq_api_key,
    )


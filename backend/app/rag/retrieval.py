"""
RAG retrieval helpers — wraps ChromaDB access.

Ported from tools/retrieval.py. Uses centralized settings.
Will be replaced by LlamaIndex service in Phase 3.
"""
import os
from app.config.settings import get_settings

settings = get_settings()

# Lazy singletons
_client = None
_embeddings = None


def _get_client():
    global _client
    if _client is None:
        import chromadb
        _client = chromadb.PersistentClient(path=settings.chroma_abs_path)
    return _client


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    return _embeddings


def get_retriever(collection_name: str, k: int = 3, where: dict | None = None):
    """Return a LangChain retriever for the given ChromaDB collection."""
    from langchain_chroma import Chroma

    db = Chroma(
        client=_get_client(),
        collection_name=collection_name,
        embedding_function=_get_embeddings(),
    )

    search_kwargs = {"k": k}
    if where:
        search_kwargs["filter"] = where

    return db.as_retriever(search_kwargs=search_kwargs)


def similarity_search(collection_name: str, query: str, k: int = 3, where: dict | None = None) -> str:
    """Convenience wrapper: returns raw context string for RAG agents."""
    try:
        retriever = get_retriever(collection_name, k=k, where=where)
        docs = retriever.invoke(query)
        return "\n\n".join(d.page_content for d in docs)
    except Exception:
        return ""


def list_collections() -> list[str]:
    """Return all known collection names in the vector store."""
    try:
        return [c.name for c in _get_client().list_collections()]
    except Exception:
        return []


def get_all_documents(collection_name: str) -> list[str]:
    """Fetch all documents from a specific collection."""
    try:
        collection = _get_client().get_collection(collection_name)
        result = collection.get()
        if result and "documents" in result and result["documents"]:
            return result["documents"]
        return []
    except Exception:
        return []

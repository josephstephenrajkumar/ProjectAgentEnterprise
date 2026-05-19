"""
LlamaIndex Service.
Handles document ingestion and retrieval using LlamaIndex and ChromaDB.
This is the foundation for Phase 3, replacing the basic LangChain retrievers.
"""
import os
from typing import List, Optional

from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from app.config.settings import get_settings

settings = get_settings()

# Lazy singletons
_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.chroma_abs_path)
    return _chroma_client


def ingest_documents(collection_name: str, documents: List[Document]) -> bool:
    """
    Ingest LlamaIndex Documents into a specific ChromaDB collection.
    """
    try:
        chroma_client = _get_chroma_client()
        chroma_collection = chroma_client.get_or_create_collection(collection_name)
        
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Build the index and store it in Chroma
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context
        )
        return True
    except Exception as e:
        print(f"Error ingesting documents into {collection_name}: {e}")
        return False


def query_collection(collection_name: str, query: str, top_k: int = 3, filters: Optional[dict] = None) -> str:
    """
    Query a specific ChromaDB collection using LlamaIndex.
    Returns the aggregated context string.
    """
    try:
        chroma_client = _get_chroma_client()
        
        # Check if collection exists
        try:
            chroma_collection = chroma_client.get_collection(collection_name)
        except Exception:
            return ""
            
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        # We don't need to rebuild the index from nodes, we just load it from the vector store
        index = VectorStoreIndex.from_vector_store(vector_store)
        
        # Configure retriever
        # Note: Advanced metadata filtering can be passed here via MetadataFilters
        retriever = index.as_retriever(similarity_top_k=top_k)
        
        nodes = retriever.retrieve(query)
        
        if not nodes:
            return ""
            
        return "\n\n".join([node.get_content() for node in nodes])
        
    except Exception as e:
        print(f"Error querying collection {collection_name}: {e}")
        return ""

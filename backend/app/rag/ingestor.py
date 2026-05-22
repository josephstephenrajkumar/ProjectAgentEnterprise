"""
Document Ingestor module for RAG.
Loads documents (SOW contracts) using UnstructuredFileLoader, chunks them,
and indexes them in ChromaDB using HuggingFace embeddings.
"""

import os
from typing import Dict, Any, Optional
from app.config.settings import get_settings

settings = get_settings()


def ingest_document(
    file_path: str,
    collection_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Ingest a single document into a ChromaDB collection.
    
    Args:
        file_path: The absolute path to the file on disk.
        collection_name: The name of the collection in ChromaDB.
        metadata: Optional dictionary of metadata to attach to all chunks.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Use UnstructuredFileLoader for all document types (Word, PDF, etc.)
    from langchain_community.document_loaders import UnstructuredFileLoader
    loader = UnstructuredFileLoader(file_path)
    docs = loader.load()

    if not docs:
        print(f"[Ingestion] ⚠️ No content found in document: {file_path}")
        return

    # Add custom metadata to all document chunks
    if metadata:
        for doc in docs:
            doc.metadata.update(metadata)

    # Split documents into chunks
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = splitter.split_documents(docs)

    # Initialize Chroma client and HuggingFace embeddings
    import chromadb
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    client = chromadb.PersistentClient(path=settings.chroma_abs_path)
    embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)

    # Add chunks to the vector store
    Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    ).add_documents(splits)
    
    print(f"[Ingestion] Successfully indexed {len(splits)} chunks from {os.path.basename(file_path)} into collection: {collection_name}")

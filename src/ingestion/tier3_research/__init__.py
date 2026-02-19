"""Tier 3 Research data sources — uploaded PDFs with RAG via ChromaDB."""

from .pdf_processor import PDFProcessor
from .embedding_client import EmbeddingClient

# VectorStore is imported lazily (chromadb has Py3.14 compat issues).
# Use:  from src.ingestion.tier3_research.vector_store import VectorStore

__all__ = ["PDFProcessor", "EmbeddingClient"]

"""Data sources API — PDF upload/indexing, semantic search, source status."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

from src.config.settings import settings
from src.storage.models import Document
from src.storage.repository import Database, DocumentRepository
from src.ingestion.tier3_research.pdf_processor import PDFProcessor
from src.ingestion.tier3_research.embedding_client import EmbeddingClient, PROVIDER_INFO

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_vector_store():
    """Lazy import to avoid chromadb module-level crash on Python 3.14."""
    from src.ingestion.tier3_research.vector_store import VectorStore
    return VectorStore()

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


VALID_PROVIDERS = ("local", "openai", "gemini")


class TextIngestRequest(BaseModel):
    """Paste raw text to chunk, embed, and store."""

    text: str = Field(..., min_length=1, max_length=500_000)
    title: str = Field(default="Pasted text", max_length=512)
    provider: str | None = Field(default=None, description="Embedding provider: local, openai, gemini")


class SearchRequest(BaseModel):
    """Semantic search request body."""

    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=50)
    document_id: str | None = Field(default=None, description="Scope search to a single document")
    provider: str | None = Field(default=None, description="Embedding provider for query")


class SearchHit(BaseModel):
    text: str
    document_id: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]
    count: int


# ── Upload ──────────────────────────────────────────────────

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    provider: str | None = Query(default=None, description="Embedding provider: local, openai, gemini"),
) -> dict[str, Any]:
    """Upload a PDF, extract text, chunk, embed, and store."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    document_id = uuid.uuid4().hex[:16]

    # 1. Extract + chunk
    processor = PDFProcessor()
    try:
        chunks, page_count = processor.process_pdf(
            contents, file.filename, extra_metadata={"document_id": document_id}
        )
    except Exception as exc:
        logger.exception("PDF processing failed for %s", file.filename)
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {exc}")

    if not chunks:
        raise HTTPException(status_code=422, detail="No extractable text found in PDF")

    # 2. Embed
    try:
        embedder = EmbeddingClient(provider=provider)
        texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(texts)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Embedding failed for %s", file.filename)
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}")

    # 3. Store vectors
    store = _get_vector_store()
    metadatas = [c.metadata for c in chunks]
    chunk_count = store.add_document(document_id, texts, embeddings, metadatas)

    # 4. Save metadata to DB
    used_provider = embedder.provider
    db = Database()
    async with db.get_session() as session:
        repo = DocumentRepository(session)
        doc = Document(
            document_id=document_id,
            filename=file.filename,
            title=file.filename.rsplit(".", 1)[0],
            source_type="pdf",
            page_count=page_count,
            chunk_count=chunk_count,
            file_size=len(contents),
            metadata_json={"embedding_provider": used_provider},
        )
        await repo.save(doc)

    logger.info(
        "Uploaded %s → %d pages, %d chunks", file.filename, page_count, chunk_count
    )

    return {
        "status": "ok",
        "document_id": document_id,
        "filename": file.filename,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "file_size": len(contents),
    }


# ── Paste Text ─────────────────────────────────────────────────

@router.post("/ingest-text")
async def ingest_text(body: TextIngestRequest) -> dict[str, Any]:
    """Ingest pasted text — chunk, embed, and store."""
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")

    document_id = uuid.uuid4().hex[:16]

    # 1. Chunk
    processor = PDFProcessor()
    chunks = processor.chunk_text(
        text,
        source_filename=body.title,
        base_metadata={"document_id": document_id},
    )
    if not chunks:
        raise HTTPException(status_code=422, detail="Could not produce any chunks")

    # 2. Embed
    try:
        embedder = EmbeddingClient(provider=body.provider)
        texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(texts)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.exception("Embedding failed for pasted text")
        raise HTTPException(status_code=502, detail=f"Embedding service error: {exc}")

    # 3. Store vectors
    store = _get_vector_store()
    metadatas = [c.metadata for c in chunks]
    chunk_count = store.add_document(document_id, texts, embeddings, metadatas)

    # 4. Save metadata to DB
    used_provider = embedder.provider
    file_size = len(text.encode("utf-8"))
    db = Database()
    async with db.get_session() as session:
        repo = DocumentRepository(session)
        doc = Document(
            document_id=document_id,
            filename=body.title,
            title=body.title,
            source_type="text",
            page_count=None,
            chunk_count=chunk_count,
            file_size=file_size,
            metadata_json={"embedding_provider": used_provider},
        )
        await repo.save(doc)

    logger.info("Ingested pasted text '%s' → %d chunks", body.title, chunk_count)

    return {
        "status": "ok",
        "document_id": document_id,
        "title": body.title,
        "chunk_count": chunk_count,
        "file_size": file_size,
    }


# ── List / Get / Delete ─────────────────────────────────────

@router.get("/documents")
async def list_documents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List all uploaded documents."""
    db = Database()
    async with db.get_session() as session:
        repo = DocumentRepository(session)
        docs = await repo.list_all(limit=limit, offset=offset)
        total = await repo.count()

    return {
        "documents": [d.to_dict() for d in docs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict[str, Any]:
    """Get metadata for a single document."""
    db = Database()
    async with db.get_session() as session:
        repo = DocumentRepository(session)
        doc = await repo.get_by_id(document_id)

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc.to_dict()


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str) -> dict[str, str]:
    """Delete a document and its ChromaDB vectors."""
    db = Database()
    async with db.get_session() as session:
        repo = DocumentRepository(session)
        found = await repo.delete(document_id)

    if not found:
        raise HTTPException(status_code=404, detail="Document not found")

    # Remove vectors
    try:
        store = _get_vector_store()
        store.delete_document(document_id)
    except Exception:
        logger.exception("Failed to delete vectors for %s", document_id)

    return {"status": "deleted", "document_id": document_id}


# ── Semantic Search ──────────────────────────────────────────

@router.post("/search")
async def search_documents(body: SearchRequest) -> SearchResponse:
    """Semantic search across all uploaded research documents."""
    try:
        embedder = EmbeddingClient(provider=body.provider)
        query_vec = embedder.embed_query(body.query)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    store = _get_vector_store()
    hits = store.search(query_vec, limit=body.limit, document_id=body.document_id)

    return SearchResponse(
        query=body.query,
        results=[
            SearchHit(
                text=h.text,
                document_id=h.document_id,
                score=h.score,
                metadata=h.metadata,
            )
            for h in hits
        ],
        count=len(hits),
    )


# ── Embedding Providers ──────────────────────────────────────

@router.get("/providers")
async def list_providers() -> dict[str, Any]:
    """List available embedding providers and which is active."""
    providers = []
    for name, info in PROVIDER_INFO.items():
        available = True
        if name == "openai" and not settings.openai_api_key:
            available = False
        elif name == "gemini" and not settings.gemini_api_key:
            available = False
        providers.append({
            "id": name,
            "label": info["label"],
            "needs_key": info["needs_key"],
            "default_model": info["default_model"],
            "available": available,
        })
    return {
        "active": settings.embedding_provider,
        "providers": providers,
    }


# ── Source Status ────────────────────────────────────────────

@router.get("/status")
async def sources_status() -> dict[str, Any]:
    """Overview of all data source connections and stats."""
    sources: list[dict[str, Any]] = [
        {
            "name": "FRED",
            "type": "tier1_core",
            "description": "Federal Reserve Economic Data — official US macro indicators",
            "status": "configured" if settings.fred_api_key else "not_configured",
            "rate_limit": f"{settings.rate_limit_fred}/min",
            "cache_ttl": f"{settings.cache_ttl_fred}s",
        },
        {
            "name": "Yahoo Finance",
            "type": "market_data",
            "description": "Equities, FX, commodities — real-time & historical prices",
            "status": "available",
            "rate_limit": f"{settings.rate_limit_yahoo}/min",
            "cache_ttl": f"{settings.cache_ttl_equity}s",
        },
        {
            "name": "CoinGecko",
            "type": "market_data",
            "description": "Cryptocurrency prices, market caps, and volumes",
            "status": "available",
            "rate_limit": f"{settings.rate_limit_coingecko}/min",
            "cache_ttl": f"{settings.cache_ttl_crypto}s",
        },
        {
            "name": "Reddit",
            "type": "tier2_sentiment",
            "description": "Social sentiment from financial subreddits",
            "status": "configured" if settings.reddit_client_id else "not_configured",
            "rate_limit": f"{settings.rate_limit_reddit}/min",
            "cache_ttl": f"{settings.cache_ttl_reddit}s",
        },
    ]

    # ChromaDB stats
    chroma_stats: dict[str, Any] = {"status": "offline", "total_chunks": 0}
    try:
        store = _get_vector_store()
        chroma_stats = {**store.collection_stats(), "status": "online"}
    except Exception:
        logger.exception("ChromaDB status check failed")

    # Document count
    doc_count = 0
    try:
        db = Database()
        async with db.get_session() as session:
            repo = DocumentRepository(session)
            doc_count = await repo.count()
    except Exception:
        pass

    sources.append({
        "name": "Research Documents (RAG)",
        "type": "tier3_research",
        "description": f"Uploaded docs indexed with ChromaDB + {settings.embedding_provider} embeddings",
        "status": "configured",
        "documents": doc_count,
        "chromadb": chroma_stats,
    })

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "sources": sources,
    }

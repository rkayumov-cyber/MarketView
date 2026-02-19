"""ChromaDB collection manager for document vectors."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from typing import Any

from src.config.settings import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "marketview_research"


@dataclass
class SearchResult:
    """A single semantic search result."""

    text: str
    document_id: str
    score: float
    metadata: dict


def _patch_pydantic_v1() -> None:
    """Monkey-patch pydantic v1 so chromadb's Settings class can load on
    Python 3.14+.  Pydantic v1's ``ModelField._set_default_and_type`` raises
    ``ConfigError`` for fields whose type is ``Undefined`` even when a valid
    annotation exists — this started failing on 3.14 due to metaclass ordering
    changes.  We replace the raiser with a fallback to ``Any``."""
    if sys.version_info < (3, 14):
        return
    try:
        import pydantic.v1.fields as pv1_fields
        from pydantic.v1.fields import Undefined

        _original = pv1_fields.ModelField._set_default_and_type

        def _patched(self: Any) -> None:
            try:
                _original(self)
            except Exception:
                # Fall back: treat as Any so the Settings class can load
                if self.type_ is Undefined:
                    self.type_ = Any
                    self.outer_type_ = Any
                    self.annotation = Any
                if self.required is False and self.get_default() is None:
                    self.allow_none = True

        pv1_fields.ModelField._set_default_and_type = _patched
    except Exception:
        pass


def _import_chromadb() -> Any:
    """Lazy-import chromadb, applying a Py3.14 compat patch first."""
    _patch_pydantic_v1()
    import chromadb
    return chromadb


class VectorStore:
    """Manage a ChromaDB collection for research documents."""

    _client: Any = None  # chromadb.ClientAPI

    @classmethod
    def get_client(cls) -> Any:
        """Get or create the persistent ChromaDB client."""
        if cls._client is None:
            chromadb = _import_chromadb()
            from chromadb.config import Settings as ChromaSettings

            cls._client = chromadb.PersistentClient(
                path=settings.chromadb_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            logger.info("ChromaDB client initialized at %s", settings.chromadb_path)
        return cls._client

    @classmethod
    def shutdown(cls) -> None:
        """Release the ChromaDB client."""
        cls._client = None
        logger.info("ChromaDB client released")

    def __init__(self) -> None:
        client = self.get_client()
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def add_document(
        self,
        document_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> int:
        """Add document chunks to the collection.

        Returns the number of chunks stored.
        """
        if not chunks:
            return 0

        ids = [f"{document_id}_{i}" for i in range(len(chunks))]

        metas = metadatas or [{} for _ in chunks]
        for m in metas:
            m["document_id"] = document_id

        self._collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metas,
        )
        logger.info("Added %d chunks for document %s", len(chunks), document_id)
        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        """Semantic search over stored chunks."""
        where_filter = {"document_id": document_id} if document_id else None

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        hits: list[SearchResult] = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                hits.append(
                    SearchResult(
                        text=doc,
                        document_id=meta.get("document_id", ""),
                        score=1.0 - dist,  # cosine distance → similarity
                        metadata=meta,
                    )
                )
        return hits

    def delete_document(self, document_id: str) -> None:
        """Remove all chunks for a document."""
        self._collection.delete(where={"document_id": document_id})
        logger.info("Deleted all chunks for document %s", document_id)

    def collection_stats(self) -> dict:
        """Return basic stats about the collection."""
        return {
            "collection": COLLECTION_NAME,
            "total_chunks": self._collection.count(),
        }

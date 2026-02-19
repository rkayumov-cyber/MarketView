"""Research context retriever for report generation.

Queries ChromaDB for document chunks relevant to each report section,
bridging the RAG pipeline into the report builder.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Section-specific search queries used to find relevant research chunks.
SECTION_QUERIES: dict[str, str] = {
    "pulse": "market regime conditions outlook risk sentiment",
    "macro": "macroeconomics inflation GDP growth monetary policy rates",
    "assets": "equities bonds forex commodities crypto prices",
    "sentiment": "market sentiment investor positioning retail institutional",
    "forward": "upcoming events risks catalysts forward outlook predictions",
}

_SCORE_THRESHOLD = 0.3
_CHUNKS_PER_SECTION = 3


@dataclass
class ResearchChunk:
    """A single retrieved research chunk."""

    text: str
    source: str  # filename or title
    document_id: str
    page: int | None
    score: float


@dataclass
class ResearchRetriever:
    """Retrieve research document chunks relevant to report sections.

    Parameters
    ----------
    document_ids:
        Optional list of document IDs to scope the search.  ``None``
        means search all documents in the vector store.
    """

    document_ids: list[str] | None = None
    _total_chunks_searched: int = field(default=0, init=False, repr=False)

    def retrieve_for_sections(self) -> dict[str, list[ResearchChunk]]:
        """Return a mapping of section name -> relevant chunks."""
        try:
            from src.ingestion.tier3_research.embedding_client import EmbeddingClient
            from src.ingestion.tier3_research.vector_store import VectorStore
        except Exception as exc:
            logger.warning("Could not import RAG components: %s", exc)
            return {}

        try:
            embedder = EmbeddingClient()
            store = VectorStore()
        except Exception as exc:
            logger.warning("Failed to initialise RAG components: %s", exc)
            return {}

        results: dict[str, list[ResearchChunk]] = {}

        for section, query in SECTION_QUERIES.items():
            try:
                embedding = embedder.embed_query(query)
            except Exception as exc:
                logger.warning("Embedding failed for section %s: %s", section, exc)
                continue

            section_chunks: list[ResearchChunk] = []

            if self.document_ids:
                # Query per-document (ChromaDB where filter is single-value)
                for doc_id in self.document_ids:
                    hits = store.search(
                        query_embedding=embedding,
                        limit=_CHUNKS_PER_SECTION,
                        document_id=doc_id,
                    )
                    self._total_chunks_searched += len(hits)
                    for hit in hits:
                        if hit.score >= _SCORE_THRESHOLD:
                            section_chunks.append(
                                ResearchChunk(
                                    text=hit.text,
                                    source=hit.metadata.get("source", hit.document_id),
                                    document_id=hit.document_id,
                                    page=hit.metadata.get("page"),
                                    score=hit.score,
                                )
                            )
            else:
                hits = store.search(
                    query_embedding=embedding,
                    limit=_CHUNKS_PER_SECTION,
                )
                self._total_chunks_searched += len(hits)
                for hit in hits:
                    if hit.score >= _SCORE_THRESHOLD:
                        section_chunks.append(
                            ResearchChunk(
                                text=hit.text,
                                source=hit.metadata.get("source", hit.document_id),
                                document_id=hit.document_id,
                                page=hit.metadata.get("page"),
                                score=hit.score,
                            )
                        )

            # Sort by score descending and keep top N
            section_chunks.sort(key=lambda c: c.score, reverse=True)
            results[section] = section_chunks[:_CHUNKS_PER_SECTION]

        return results

    @property
    def total_chunks_searched(self) -> int:
        return self._total_chunks_searched

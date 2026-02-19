"""Multi-provider embedding client — local (sentence-transformers), OpenAI, or Gemini."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Literal

from src.config.settings import settings

logger = logging.getLogger(__name__)

Provider = Literal["local", "openai", "gemini"]

# Provider names shown to the frontend
PROVIDER_INFO: dict[str, dict] = {
    "local": {
        "label": "Local (sentence-transformers)",
        "needs_key": False,
        "default_model": "all-MiniLM-L6-v2",
    },
    "openai": {
        "label": "OpenAI",
        "needs_key": True,
        "default_model": "text-embedding-3-small",
    },
    "gemini": {
        "label": "Google Gemini",
        "needs_key": True,
        "default_model": "text-embedding-004",
    },
}


# ── Abstract base ────────────────────────────────────────────

class _BaseEmbedder(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


# ── Local (sentence-transformers) ────────────────────────────

class _LocalEmbedder(_BaseEmbedder):
    _model = None

    def __init__(self, model_name: str | None = None) -> None:
        name = model_name or settings.local_embedding_model
        if _LocalEmbedder._model is None or _LocalEmbedder._model_name != name:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading local embedding model: %s", name)
            _LocalEmbedder._model = SentenceTransformer(name)
            _LocalEmbedder._model_name = name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = _LocalEmbedder._model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]


# ── OpenAI ───────────────────────────────────────────────────

class _OpenAIEmbedder(_BaseEmbedder):
    def __init__(self, model: str | None = None) -> None:
        key = settings.openai_api_key
        if key is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import OpenAI
        self._client = OpenAI(api_key=key.get_secret_value())
        self.model = model or settings.embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch_size = 512
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.embeddings.create(input=batch, model=self.model)
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings


# ── Gemini ───────────────────────────────────────────────────

class _GeminiEmbedder(_BaseEmbedder):
    def __init__(self, model: str | None = None) -> None:
        key = settings.gemini_api_key
        if key is None:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai
        self._client = genai.Client(api_key=key.get_secret_value())
        self.model = model or settings.gemini_embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batch_size = 100  # Gemini batch limit
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = self._client.models.embed_content(
                model=self.model,
                contents=batch,
            )
            all_embeddings.extend([e.values for e in result.embeddings])
        return all_embeddings


# ── Factory ──────────────────────────────────────────────────

_PROVIDERS: dict[str, type[_BaseEmbedder]] = {
    "local": _LocalEmbedder,
    "openai": _OpenAIEmbedder,
    "gemini": _GeminiEmbedder,
}


class EmbeddingClient(_BaseEmbedder):
    """Unified embedding client.  Provider chosen by:
    1. explicit ``provider`` arg
    2. ``EMBEDDING_PROVIDER`` env / settings default
    """

    def __init__(self, provider: Provider | None = None) -> None:
        name = provider or settings.embedding_provider
        cls = _PROVIDERS.get(name)
        if cls is None:
            raise ValueError(f"Unknown embedding provider: {name}")
        self._inner = cls()
        self.provider = name

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(text)

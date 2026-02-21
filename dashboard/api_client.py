"""Centralized httpx client for all backend API calls."""

import logging
import os
from typing import Any

import httpx
import streamlit as st

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = os.environ.get("MARKETVIEW_API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 15.0
REPORT_TIMEOUT = 120.0


def _base_url() -> str:
    return st.session_state.get("api_base_url", DEFAULT_BASE_URL)


def _auth_headers() -> dict[str, str]:
    """Return X-API-Key header if configured via env or session state."""
    key = st.session_state.get("api_key") or os.environ.get("MARKETVIEW_API_KEY", "")
    if key:
        return {"X-API-Key": key}
    return {}


def _get(
    path: str,
    params: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """GET request, returns parsed JSON or None on failure."""
    try:
        resp = httpx.get(
            f"{_base_url()}{path}", params=params, timeout=timeout,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.warning("GET %s failed: %s", path, e)
        return None


def _post(
    path: str,
    json: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """POST request with JSON body."""
    try:
        resp = httpx.post(
            f"{_base_url()}{path}", json=json, timeout=timeout,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.warning("POST %s failed: %s", path, e)
        return None


def _post_multipart(
    path: str,
    files: dict,
    params: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """POST request with multipart file upload."""
    try:
        resp = httpx.post(
            f"{_base_url()}{path}",
            files=files,
            params=params,
            timeout=timeout,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.warning("POST multipart %s failed: %s", path, e)
        return None


def _delete(
    path: str, timeout: float = DEFAULT_TIMEOUT,
) -> dict | None:
    """DELETE request."""
    try:
        resp = httpx.delete(
            f"{_base_url()}{path}", timeout=timeout,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        logger.warning("DELETE %s failed: %s", path, e)
        return None


def _get_raw(
    path: str,
    params: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> bytes | None:
    """GET request returning raw bytes (for file downloads)."""
    try:
        resp = httpx.get(
            f"{_base_url()}{path}", params=params, timeout=timeout,
            headers=_auth_headers(),
        )
        resp.raise_for_status()
        return resp.content
    except httpx.HTTPError as e:
        logger.warning("GET raw %s failed: %s", path, e)
        return None


# ── Health ──────────────────────────────────────────────────


def check_backend_health() -> dict | None:
    return _get("/health")


# ── Market Data ─────────────────────────────────────────────


def _source_param() -> dict:
    source = st.session_state.get("data_source", "live")
    return {"source": source}


def fetch_snapshot() -> dict | None:
    return _get(
        "/api/v1/data/market/snapshot", params=_source_param(),
    )


def fetch_equities() -> dict | None:
    return _get(
        "/api/v1/data/market/equities", params=_source_param(),
    )


def fetch_fx() -> dict | None:
    return _get(
        "/api/v1/data/market/fx", params=_source_param(),
    )


def fetch_commodities() -> dict | None:
    return _get(
        "/api/v1/data/market/commodities", params=_source_param(),
    )


def fetch_crypto() -> dict | None:
    return _get(
        "/api/v1/data/market/crypto", params=_source_param(),
    )


# ── Research Sources ────────────────────────────────────────


def upload_document(
    file_name: str,
    file_bytes: bytes,
    provider: str | None = None,
) -> dict | None:
    files = {"file": (file_name, file_bytes, "application/pdf")}
    params = {"provider": provider} if provider else None
    return _post_multipart(
        "/api/v1/sources/upload",
        files=files,
        params=params,
        timeout=60.0,
    )


def ingest_text(
    text: str,
    title: str = "Pasted text",
    provider: str | None = None,
) -> dict | None:
    body: dict[str, Any] = {"text": text, "title": title}
    if provider:
        body["provider"] = provider
    return _post("/api/v1/sources/ingest-text", json=body)


def list_documents() -> dict | None:
    return _get("/api/v1/sources/documents")


def delete_document(doc_id: str) -> dict | None:
    return _delete(f"/api/v1/sources/documents/{doc_id}")


def search_documents(
    query: str,
    limit: int = 5,
    document_id: str | None = None,
    provider: str | None = None,
) -> dict | None:
    body: dict[str, Any] = {"query": query, "limit": limit}
    if document_id:
        body["document_id"] = document_id
    if provider:
        body["provider"] = provider
    return _post("/api/v1/sources/search", json=body)


def get_embedding_providers() -> dict | None:
    return _get("/api/v1/sources/providers")


# ── Reports ─────────────────────────────────────────────────


def generate_report(request_body: dict) -> dict | None:
    return _post(
        "/api/v1/reports/generate",
        json=request_body,
        timeout=REPORT_TIMEOUT,
    )


def generate_quick_report(level: int = 1) -> dict | None:
    return _get(
        "/api/v1/reports/generate/quick",
        params={"level": level},
        timeout=REPORT_TIMEOUT,
    )


def get_llm_providers() -> dict | None:
    return _get("/api/v1/reports/llm-providers")


def list_reports(limit: int = 10, offset: int = 0) -> dict | None:
    return _get("/api/v1/reports/", params={"limit": limit, "offset": offset})


def get_report(report_id: str) -> dict | None:
    return _get(f"/api/v1/reports/{report_id}")


def download_report(
    report_id: str, fmt: str = "markdown",
) -> bytes | None:
    return _get_raw(
        f"/api/v1/reports/{report_id}/download",
        params={"format": fmt},
    )


def delete_report(report_id: str) -> dict | None:
    return _delete(f"/api/v1/reports/{report_id}")


# ── Templates ───────────────────────────────────────────────


def list_templates() -> dict | None:
    return _get("/api/v1/templates/")

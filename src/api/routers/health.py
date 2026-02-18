"""Health check endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter

from src.config.settings import settings
from src.ingestion.base import CacheManager
from src.ingestion.tier1_core import FREDClient

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "environment": settings.app_env,
    }


@router.get("/health/detailed")
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check with service status."""
    services: dict[str, Any] = {}

    # Check Redis
    cache = CacheManager()
    try:
        await cache.connect()
        await cache.set("health_check", "ok", ttl=10)
        result = await cache.get("health_check")
        services["redis"] = {
            "status": "healthy" if result == "ok" else "degraded",
            "latency_ms": 0,  # Could add timing
        }
    except Exception as e:
        services["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check FRED API
    fred = FREDClient()
    try:
        is_healthy = await fred.health_check()
        services["fred"] = {"status": "healthy" if is_healthy else "unavailable"}
    except Exception as e:
        services["fred"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(s.get("status") == "healthy" for s in services.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Kubernetes readiness probe."""
    # Check critical services
    cache = CacheManager()
    try:
        await cache.connect()
        return {"status": "ready"}
    except Exception:
        return {"status": "not_ready"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe."""
    return {"status": "alive"}

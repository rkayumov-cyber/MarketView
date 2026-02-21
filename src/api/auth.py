"""API key authentication dependency."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from src.config.settings import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """Validate the X-API-Key header if API_KEY is configured.

    When settings.api_key is unset (None), authentication is disabled
    and all requests pass through — suitable for local development.
    When set, every request must include a matching X-API-Key header.
    """
    expected = settings.api_key
    if expected is None or not expected.get_secret_value():
        return None  # Auth disabled (no key configured)

    if not api_key or api_key != expected.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key

"""Multi-provider async LLM client — OpenAI, Gemini, Anthropic, or Ollama."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Literal

from src.config.settings import settings

logger = logging.getLogger(__name__)

LLMProvider = Literal["openai", "gemini", "anthropic", "ollama"]

# Provider metadata for frontend consumption
LLM_PROVIDER_INFO: dict[str, dict] = {
    "openai": {
        "label": "OpenAI",
        "type": "closed",
        "needs_key": True,
        "env_var": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini"],
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "label": "Google Gemini",
        "type": "closed",
        "needs_key": True,
        "env_var": "GEMINI_API_KEY",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        "default_model": "gemini-2.0-flash",
    },
    "anthropic": {
        "label": "Anthropic",
        "type": "closed",
        "needs_key": True,
        "env_var": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4-20250514"],
        "default_model": "claude-sonnet-4-20250514",
    },
    "ollama": {
        "label": "Ollama (Local)",
        "type": "open",
        "needs_key": False,
        "env_var": None,
        "models": ["llama3.2", "mistral", "gemma2"],
        "default_model": "llama3.2",
    },
}


# ── Abstract base ────────────────────────────────────────────


class _BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str: ...


# ── OpenAI ───────────────────────────────────────────────────


class _OpenAILLMClient(_BaseLLMClient):
    def __init__(self, model: str | None = None) -> None:
        key = settings.openai_api_key
        if key is None:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=key.get_secret_value())
        self.model = model or LLM_PROVIDER_INFO["openai"]["default_model"]

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        response = await self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""


# ── Gemini ───────────────────────────────────────────────────


class _GeminiLLMClient(_BaseLLMClient):
    def __init__(self, model: str | None = None) -> None:
        key = settings.gemini_api_key
        if key is None:
            raise RuntimeError("GEMINI_API_KEY is not configured")
        from google import genai

        self._client = genai.Client(api_key=key.get_secret_value())
        self.model = model or LLM_PROVIDER_INFO["gemini"]["default_model"]

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import asyncio

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self.model,
            contents=full_prompt,
        )
        return response.text or ""


# ── Anthropic ────────────────────────────────────────────────


class _AnthropicLLMClient(_BaseLLMClient):
    def __init__(self, model: str | None = None) -> None:
        key = settings.anthropic_api_key
        if key is None:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=key.get_secret_value())
        self.model = model or LLM_PROVIDER_INFO["anthropic"]["default_model"]

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = await self._client.messages.create(**kwargs)
        return response.content[0].text


# ── Ollama ───────────────────────────────────────────────────


class _OllamaLLMClient(_BaseLLMClient):
    def __init__(self, model: str | None = None) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self.model = model or LLM_PROVIDER_INFO["ollama"]["default_model"]

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        import httpx

        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/generate", json=payload
            )
            resp.raise_for_status()
            return resp.json().get("response", "")


# ── Factory ──────────────────────────────────────────────────

_PROVIDERS: dict[str, type[_BaseLLMClient]] = {
    "openai": _OpenAILLMClient,
    "gemini": _GeminiLLMClient,
    "anthropic": _AnthropicLLMClient,
    "ollama": _OllamaLLMClient,
}


class LLMClient(_BaseLLMClient):
    """Unified async LLM client. Provider chosen by explicit arg."""

    def __init__(
        self, provider: LLMProvider, model: str | None = None
    ) -> None:
        cls = _PROVIDERS.get(provider)
        if cls is None:
            raise ValueError(f"Unknown LLM provider: {provider}")
        self._inner = cls(model=model)
        self.provider = provider
        self.model = model or LLM_PROVIDER_INFO[provider]["default_model"]

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        return await self._inner.generate(prompt, system_prompt)

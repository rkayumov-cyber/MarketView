"""Prompt template CRUD API endpoints."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.storage.repository import Database, PromptTemplateRepository
from src.storage.models import PromptTemplate

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Default templates seeded on first run ───────────────────

_DEFAULT_TEMPLATES = [
    {
        "name": "Risk Assessment",
        "description": "Focus on risk factors and downside scenarios",
        "prompt_text": (
            "Focus on risk factors, tail events, hedging strategies, "
            "and downside scenarios across all asset classes."
        ),
    },
    {
        "name": "Sector Deep Dive",
        "description": "Detailed sector-by-sector analysis",
        "prompt_text": (
            "Provide detailed sector-by-sector analysis with relative performance, "
            "rotation signals, and sector-specific catalysts."
        ),
    },
    {
        "name": "Earnings Focus",
        "description": "Emphasize corporate earnings trends",
        "prompt_text": (
            "Emphasize corporate earnings trends, guidance revisions, "
            "valuation metrics, and earnings surprise impacts on market direction."
        ),
    },
    {
        "name": "Macro Outlook",
        "description": "Prioritize macroeconomic analysis",
        "prompt_text": (
            "Prioritize macroeconomic analysis: central bank policy, inflation dynamics, "
            "growth trajectory, and cross-regional economic divergences."
        ),
    },
]


async def seed_defaults() -> None:
    """Create built-in templates if the table is empty."""
    db = Database()
    async with db.get_session() as session:
        repo = PromptTemplateRepository(session)
        if await repo.count() > 0:
            return
        for tpl in _DEFAULT_TEMPLATES:
            template = PromptTemplate(
                template_id=f"tpl-{uuid.uuid4().hex[:12]}",
                name=tpl["name"],
                description=tpl["description"],
                prompt_text=tpl["prompt_text"],
                is_default=True,
            )
            await repo.save(template)
        logger.info("Seeded %d default prompt templates", len(_DEFAULT_TEMPLATES))


# ── Request / Response schemas ──────────────────────────────

class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    prompt_text: str = Field(..., min_length=1)


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    prompt_text: str | None = Field(default=None, min_length=1)


# ── Endpoints ───────────────────────────────────────────────

@router.get("/")
async def list_templates() -> dict[str, Any]:
    """List all prompt templates."""
    db = Database()
    async with db.get_session() as session:
        repo = PromptTemplateRepository(session)
        templates = await repo.list_all()
        return {
            "templates": [t.to_dict() for t in templates],
            "total": await repo.count(),
        }


@router.post("/", status_code=201)
async def create_template(body: TemplateCreate) -> dict[str, Any]:
    """Create a new prompt template."""
    db = Database()
    async with db.get_session() as session:
        repo = PromptTemplateRepository(session)
        template = PromptTemplate(
            template_id=f"tpl-{uuid.uuid4().hex[:12]}",
            name=body.name,
            description=body.description,
            prompt_text=body.prompt_text,
            is_default=False,
        )
        saved = await repo.save(template)
        return saved.to_dict()


@router.put("/{template_id}")
async def update_template(template_id: str, body: TemplateUpdate) -> dict[str, Any]:
    """Update an existing prompt template."""
    db = Database()
    async with db.get_session() as session:
        repo = PromptTemplateRepository(session)
        tpl = await repo.get_by_id(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        if body.name is not None:
            tpl.name = body.name
        if body.description is not None:
            tpl.description = body.description
        if body.prompt_text is not None:
            tpl.prompt_text = body.prompt_text
        await session.commit()
        await session.refresh(tpl)
        return tpl.to_dict()


@router.delete("/{template_id}")
async def delete_template(template_id: str) -> dict[str, str]:
    """Delete a prompt template (built-in defaults cannot be deleted)."""
    db = Database()
    async with db.get_session() as session:
        repo = PromptTemplateRepository(session)
        tpl = await repo.get_by_id(template_id)
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        if tpl.is_default:
            raise HTTPException(status_code=403, detail="Cannot delete built-in template")
        await repo.delete(template_id)
        return {"status": "deleted", "template_id": template_id}

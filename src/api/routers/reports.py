"""Report generation API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from src.reports.models import ReportLevel, ReportFormat, ReportConfig
from src.reports.builder import ReportBuilder
from src.reports.formatters import MarkdownFormatter, PDFFormatter

router = APIRouter()


class ReportRequest(BaseModel):
    """Report generation request."""

    level: int = Field(default=2, ge=1, le=3, description="Report depth level (1-3)")
    format: str = Field(default="markdown", description="Output format")
    include_technicals: bool = Field(default=True, description="Include technical analysis")
    include_sentiment: bool = Field(default=True, description="Include sentiment analysis")
    include_correlations: bool = Field(default=False, description="Include correlation matrix")
    assets: list[str] | None = Field(default=None, description="Specific assets to analyze")
    title: str | None = Field(default=None, description="Custom report title")
    llm_provider: str | None = Field(default=None, description="LLM provider for AI enhancement")
    llm_model: str | None = Field(default=None, description="LLM model name")


class ReportResponse(BaseModel):
    """Report generation response."""

    report_id: str
    status: str
    created_at: datetime
    level: int
    format: str
    content: str | None = None
    download_url: str | None = None


# In-memory storage for demo (would use database in production)
_reports_cache: dict[str, dict[str, Any]] = {}


@router.post("/generate")
async def generate_report(request: ReportRequest) -> ReportResponse:
    """Generate a new market analysis report."""
    try:
        # Create config
        config = ReportConfig(
            level=ReportLevel(request.level),
            format=ReportFormat(request.format),
            include_technicals=request.include_technicals,
            include_sentiment=request.include_sentiment,
            include_correlations=request.include_correlations,
            custom_assets=request.assets,
            title=request.title,
            llm_provider=request.llm_provider,
            llm_model=request.llm_model,
        )

        # Build report
        builder = ReportBuilder()
        report = await builder.build(config)

        # Format output
        if request.format == "markdown":
            formatter = MarkdownFormatter()
            content = formatter.format(report)
        elif request.format == "json":
            content = report.model_dump_json(indent=2)
        else:
            formatter = MarkdownFormatter()
            content = formatter.format(report)

        # Cache the report
        _reports_cache[report.report_id] = {
            "report": report,
            "content": content,
            "format": request.format,
        }

        return ReportResponse(
            report_id=report.report_id,
            status="completed",
            created_at=report.created_at,
            level=request.level,
            format=request.format,
            content=content,
            download_url=f"/api/v1/reports/{report.report_id}/download",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get("/generate/quick")
async def generate_quick_report(
    level: int = Query(default=1, ge=1, le=3, description="Report level"),
) -> dict[str, Any]:
    """Generate a quick synchronous report."""
    try:
        builder = ReportBuilder()

        if level == 1:
            report = await builder.build_quick()
        elif level == 2:
            report = await builder.build_standard()
        else:
            report = await builder.build_deep_dive()

        formatter = MarkdownFormatter()
        content = formatter.format(report)

        # Cache the report
        _reports_cache[report.report_id] = {
            "report": report,
            "content": content,
            "format": "markdown",
        }

        return {
            "report_id": report.report_id,
            "status": "completed",
            "created_at": report.created_at.isoformat(),
            "level": level,
            "title": report.title,
            "content": content,
            "download_url": f"/api/v1/reports/{report.report_id}/download",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quick report generation failed: {str(e)}",
        )


@router.get("/llm-providers")
async def get_llm_providers() -> dict[str, Any]:
    """Return available LLM providers with availability status."""
    from src.config.settings import settings
    from src.llm.client import LLM_PROVIDER_INFO

    providers = []
    for name, info in LLM_PROVIDER_INFO.items():
        available = False
        if name == "openai":
            available = settings.openai_api_key is not None
        elif name == "gemini":
            available = settings.gemini_api_key is not None
        elif name == "anthropic":
            available = settings.anthropic_api_key is not None
        elif name == "ollama":
            try:
                import httpx

                resp = httpx.get(
                    f"{settings.ollama_base_url}/api/tags", timeout=2.0
                )
                available = resp.status_code == 200
            except Exception:
                available = False

        providers.append(
            {
                "id": name,
                "label": info["label"],
                "type": info["type"],
                "needs_key": info["needs_key"],
                "models": info["models"],
                "default_model": info["default_model"],
                "available": available,
            }
        )

    return {"providers": providers}


@router.get("/{report_id}")
async def get_report(report_id: str) -> dict[str, Any]:
    """Get a specific report by ID."""
    if report_id not in _reports_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_id} not found",
        )

    cached = _reports_cache[report_id]
    report = cached["report"]

    return {
        "report_id": report.report_id,
        "title": report.title,
        "level": report.level.value,
        "created_at": report.created_at.isoformat(),
        "content": cached["content"],
        "format": cached["format"],
    }


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = Query(default="markdown", description="Output format"),
) -> Response:
    """Download a report in specified format."""
    if report_id not in _reports_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_id} not found",
        )

    cached = _reports_cache[report_id]
    report = cached["report"]

    if format == "markdown":
        formatter = MarkdownFormatter()
        content = formatter.format(report)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={report_id}.md"
            },
        )

    elif format == "pdf":
        try:
            pdf_formatter = PDFFormatter()
            pdf_bytes = pdf_formatter.format_pdf(report)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.pdf"
                },
            )
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF generation requires WeasyPrint. Install with: pip install weasyprint",
            )

    elif format == "json":
        return Response(
            content=report.model_dump_json(indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename={report_id}.json"
            },
        )

    elif format == "html":
        try:
            pdf_formatter = PDFFormatter()
            html_content = pdf_formatter.format_html(report)
            return Response(
                content=html_content,
                media_type="text/html",
                headers={
                    "Content-Disposition": f"attachment; filename={report_id}.html"
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"HTML generation failed: {str(e)}",
            )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {format}. Use markdown, pdf, json, or html.",
        )


@router.get("/")
async def list_reports(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """List recent reports."""
    reports = []

    for report_id, cached in list(_reports_cache.items())[offset:offset + limit]:
        report = cached["report"]
        reports.append({
            "report_id": report.report_id,
            "title": report.title,
            "level": report.level.value,
            "created_at": report.created_at.isoformat(),
            "format": cached["format"],
        })

    return {
        "reports": reports,
        "total": len(_reports_cache),
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{report_id}")
async def delete_report(report_id: str) -> dict[str, str]:
    """Delete a report."""
    if report_id not in _reports_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Report {report_id} not found",
        )

    del _reports_cache[report_id]

    return {"status": "deleted", "report_id": report_id}

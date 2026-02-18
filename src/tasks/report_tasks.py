"""Celery tasks for report generation."""

import asyncio
import logging
from datetime import datetime

from celery import shared_task

from src.reports.models import ReportConfig, ReportLevel
from src.reports.builder import ReportBuilder
from src.reports.formatters import MarkdownFormatter, PDFFormatter

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async function in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(bind=True, name="src.tasks.report_tasks.generate_report_task")
def generate_report_task(
    self,
    level: int = 2,
    format: str = "markdown",
    include_technicals: bool = True,
    include_correlations: bool = False,
    output_path: str | None = None,
) -> dict:
    """Generate a market analysis report asynchronously.

    Args:
        level: Report depth level (1-3)
        format: Output format (markdown, pdf, html)
        include_technicals: Include technical analysis
        include_correlations: Include correlation matrix
        output_path: Optional file path to save report

    Returns:
        Dict with report_id, status, and content/path
    """
    logger.info(f"Starting report generation task: level={level}, format={format}")

    try:
        # Update task state
        self.update_state(state="PROGRESS", meta={"status": "Building report..."})

        # Create config
        config = ReportConfig(
            level=ReportLevel(level),
            include_technicals=include_technicals,
            include_correlations=include_correlations,
        )

        # Build report
        builder = ReportBuilder()
        report = run_async(builder.build(config))

        self.update_state(state="PROGRESS", meta={"status": "Formatting output..."})

        # Format output
        if format == "markdown":
            formatter = MarkdownFormatter()
            content = formatter.format(report)
            if output_path:
                with open(output_path, "w") as f:
                    f.write(content)
        elif format == "pdf":
            formatter = PDFFormatter()
            if output_path:
                formatter.save(report, output_path)
                content = f"PDF saved to {output_path}"
            else:
                content = "PDF generated (no output path specified)"
        else:
            formatter = MarkdownFormatter()
            content = formatter.format(report)

        logger.info(f"Report generated successfully: {report.report_id}")

        return {
            "report_id": report.report_id,
            "status": "completed",
            "title": report.title,
            "created_at": report.created_at.isoformat(),
            "output_path": output_path,
            "content_preview": content[:500] if content else None,
        }

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise


@shared_task(name="src.tasks.report_tasks.schedule_daily_report")
def schedule_daily_report(level: int = 2) -> dict:
    """Generate the daily alpha brief.

    This is typically scheduled to run before market open.
    """
    logger.info("Generating scheduled daily report")

    timestamp = datetime.utcnow().strftime("%Y%m%d")
    output_path = f"./reports/daily_alpha_brief_{timestamp}.md"

    # Trigger the report generation task
    result = generate_report_task.delay(
        level=level,
        format="markdown",
        include_technicals=True,
        include_correlations=level == 3,
        output_path=output_path,
    )

    return {
        "task_id": result.id,
        "scheduled_at": datetime.utcnow().isoformat(),
        "output_path": output_path,
    }


@shared_task(name="src.tasks.report_tasks.generate_pdf_report")
def generate_pdf_report(report_id: str, output_path: str | None = None) -> dict:
    """Generate PDF version of an existing report."""
    # This would retrieve the report from storage and convert to PDF
    # Placeholder implementation
    return {
        "status": "not_implemented",
        "message": "PDF generation from stored reports requires database integration",
    }

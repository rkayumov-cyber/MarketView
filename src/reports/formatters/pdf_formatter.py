"""PDF report formatter using WeasyPrint."""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config.settings import settings
from src.reports.models import Report
from src.reports.formatters.markdown_formatter import MarkdownFormatter


class PDFFormatter:
    """Formats reports as PDF using WeasyPrint."""

    TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

    def __init__(self) -> None:
        self.markdown_formatter = MarkdownFormatter()
        self._env = None

    @property
    def env(self) -> Environment:
        """Get Jinja2 environment."""
        if self._env is None:
            # Create templates directory if it doesn't exist
            self.TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

            self._env = Environment(
                loader=FileSystemLoader(str(self.TEMPLATE_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        return self._env

    def format_html(self, report: Report) -> str:
        """Format report as HTML for PDF conversion."""
        # Convert markdown to HTML first
        md_content = self.markdown_formatter.format(report)

        # Use markdown library if available, otherwise basic conversion
        try:
            import markdown
            html_content = markdown.markdown(
                md_content,
                extensions=["tables", "fenced_code"],
            )
        except ImportError:
            # Basic conversion without markdown library
            html_content = self._basic_md_to_html(md_content)

        # Wrap in HTML template
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report.title}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>"""

        return html

    def format_pdf(self, report: Report, output_path: str | None = None) -> bytes:
        """Format report as PDF.

        Args:
            report: Report to format
            output_path: Optional path to save PDF file

        Returns:
            PDF bytes
        """
        try:
            from weasyprint import HTML
        except ImportError:
            raise ImportError(
                "WeasyPrint is required for PDF generation. "
                "Install with: pip install weasyprint"
            )

        html_content = self.format_html(report)
        html = HTML(string=html_content)

        if output_path:
            # Ensure directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            html.write_pdf(output_path)
            with open(output_path, "rb") as f:
                return f.read()
        else:
            return html.write_pdf()

    def save(self, report: Report, filename: str | None = None) -> str:
        """Save report as PDF file.

        Args:
            report: Report to save
            filename: Optional filename (default: report_id.pdf)

        Returns:
            Path to saved file
        """
        if filename is None:
            filename = f"{report.report_id}.pdf"

        output_dir = Path(settings.report_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / filename
        self.format_pdf(report, str(output_path))

        return str(output_path)

    def _get_css(self) -> str:
        """Get CSS styles for PDF."""
        return """
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }

        .container {
            max-width: 100%;
        }

        h1 {
            font-size: 24pt;
            color: #1a1a2e;
            border-bottom: 3px solid #4a90d9;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        h2 {
            font-size: 18pt;
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-after: avoid;
        }

        h3 {
            font-size: 14pt;
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        p {
            margin-bottom: 10px;
        }

        ul, ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }

        li {
            margin-bottom: 5px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 10pt;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }

        th {
            background-color: #4a90d9;
            color: white;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background-color: #f9f9f9;
        }

        strong {
            color: #2c3e50;
        }

        em {
            color: #666;
        }

        hr {
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }

        .bullish {
            color: #27ae60;
        }

        .bearish {
            color: #e74c3c;
        }

        .neutral {
            color: #f39c12;
        }

        code {
            background-color: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }

        blockquote {
            border-left: 4px solid #4a90d9;
            margin: 15px 0;
            padding: 10px 20px;
            background-color: #f9f9f9;
        }

        /* Page breaks */
        h2 {
            page-break-before: auto;
        }

        table, figure {
            page-break-inside: avoid;
        }
        """

    def _basic_md_to_html(self, md: str) -> str:
        """Basic Markdown to HTML conversion."""
        import re

        html = md

        # Headers
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

        # Lists
        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)

        # Horizontal rules
        html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)

        # Paragraphs
        paragraphs = html.split("\n\n")
        html = "\n".join(
            f"<p>{p}</p>" if not p.startswith("<") else p
            for p in paragraphs
        )

        return html

"""Extract text from PDFs and chunk with overlap."""

from dataclasses import dataclass

from pypdf import PdfReader

from src.config.settings import settings


@dataclass
class TextChunk:
    """A single chunk of document text."""

    text: str
    page: int
    chunk_index: int
    metadata: dict


class PDFProcessor:
    """Extract and chunk text from PDF files."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def extract_text(self, file_bytes: bytes) -> tuple[str, int]:
        """Extract all text from a PDF.

        Returns (full_text, page_count).
        """
        import io

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n\n".join(pages), len(reader.pages)

    def extract_pages(self, file_bytes: bytes) -> list[tuple[int, str]]:
        """Extract text per page. Returns list of (page_number, text)."""
        import io

        reader = PdfReader(io.BytesIO(file_bytes))
        return [
            (i + 1, page.extract_text() or "")
            for i, page in enumerate(reader.pages)
        ]

    def chunk_text(
        self,
        text: str,
        source_filename: str = "",
        base_metadata: dict | None = None,
    ) -> list[TextChunk]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        meta = base_metadata or {}
        chunks: list[TextChunk] = []
        start = 0
        idx = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to break at a sentence or paragraph boundary
            if end < len(text):
                for sep in ("\n\n", "\n", ". ", " "):
                    last = chunk_text.rfind(sep)
                    if last > self.chunk_size // 2:
                        chunk_text = chunk_text[: last + len(sep)]
                        end = start + len(chunk_text)
                        break

            chunks.append(
                TextChunk(
                    text=chunk_text.strip(),
                    page=0,  # Set later if per-page chunking is used
                    chunk_index=idx,
                    metadata={
                        **meta,
                        "source": source_filename,
                        "chunk_index": idx,
                    },
                )
            )

            start = end - self.chunk_overlap
            if start <= chunks[-1].chunk_index and start < end:
                start = end  # Prevent infinite loop on tiny overlaps
            idx += 1

        return chunks

    def process_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        extra_metadata: dict | None = None,
    ) -> tuple[list[TextChunk], int]:
        """Full pipeline: extract → chunk. Returns (chunks, page_count)."""
        pages = self.extract_pages(file_bytes)
        page_count = len(pages)
        meta = extra_metadata or {}

        all_chunks: list[TextChunk] = []
        global_idx = 0

        for page_num, page_text in pages:
            if not page_text.strip():
                continue

            page_chunks = self.chunk_text(
                page_text,
                source_filename=filename,
                base_metadata={**meta, "page": page_num},
            )
            for chunk in page_chunks:
                chunk.page = page_num
                chunk.chunk_index = global_idx
                chunk.metadata["chunk_index"] = global_idx
                all_chunks.append(chunk)
                global_idx += 1

        return all_chunks, page_count

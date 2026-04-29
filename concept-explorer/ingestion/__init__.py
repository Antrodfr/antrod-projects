"""Ingestion module for multi-format document parsing."""

from ingestion.base import Document, Ingestor
from ingestion.pdf_ingestor import PDFIngestor
from ingestion.docx_ingestor import DocxIngestor
from ingestion.pptx_ingestor import PptxIngestor
from ingestion.image_ingestor import ImageIngestor
from ingestion.markdown_ingestor import MarkdownIngestor

INGESTORS: dict[str, type[Ingestor]] = {
    ".pdf": PDFIngestor,
    ".docx": DocxIngestor,
    ".pptx": PptxIngestor,
    ".png": ImageIngestor,
    ".jpg": ImageIngestor,
    ".jpeg": ImageIngestor,
    ".md": MarkdownIngestor,
    ".markdown": MarkdownIngestor,
}


def get_ingestor(file_path: str) -> Ingestor:
    """Return the appropriate ingestor for a given file path."""
    from pathlib import Path

    ext = Path(file_path).suffix.lower()
    ingestor_cls = INGESTORS.get(ext)
    if ingestor_cls is None:
        raise ValueError(f"Unsupported file format: {ext}")
    return ingestor_cls()


__all__ = [
    "Document",
    "Ingestor",
    "PDFIngestor",
    "DocxIngestor",
    "PptxIngestor",
    "ImageIngestor",
    "MarkdownIngestor",
    "get_ingestor",
    "INGESTORS",
]

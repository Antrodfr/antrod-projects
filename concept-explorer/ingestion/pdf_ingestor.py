"""PDF document ingestion using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

from ingestion.base import Document, Ingestor


class PDFIngestor(Ingestor):
    """Extract text and images from PDF files using PyMuPDF (fitz)."""

    def ingest(self, file_path: str | Path) -> Document:
        path = self._validate_path(file_path)
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError("pymupdf is required: pip install pymupdf") from exc

        text_chunks: list[str] = []
        images: list[bytes] = []

        with fitz.open(str(path)) as pdf:
            metadata = {
                "format": "pdf",
                "filename": path.name,
                "pages": str(len(pdf)),
            }
            for page_num, page in enumerate(pdf):
                text = page.get_text()
                if text.strip():
                    text_chunks.append(text.strip())

                for img_info in page.get_images(full=True):
                    try:
                        xref = img_info[0]
                        base_image = pdf.extract_image(xref)
                        if base_image and base_image.get("image"):
                            images.append(base_image["image"])
                    except Exception:
                        continue

        return Document(text_chunks=text_chunks, images=images, metadata=metadata)

"""Image ingestion with base64 encoding for AI vision APIs."""

from __future__ import annotations

import base64
from pathlib import Path

from ingestion.base import Document, Ingestor


class ImageIngestor(Ingestor):
    """Accept PNG/JPG images and encode for Mistral Vision API (OCR)."""

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    def ingest(self, file_path: str | Path) -> Document:
        path = self._validate_path(file_path)

        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image format: {path.suffix}")

        image_bytes = path.read_bytes()

        mime_type = self._get_mime_type(path.suffix.lower())
        b64 = base64.b64encode(image_bytes).decode("utf-8")

        metadata = {
            "format": "image",
            "filename": path.name,
            "mime_type": mime_type,
            "base64_uri": f"data:{mime_type};base64,{b64}",
            "size_bytes": str(len(image_bytes)),
        }

        return Document(
            text_chunks=[f"[Image: {path.name}]"],
            images=[image_bytes],
            metadata=metadata,
        )

    @staticmethod
    def _get_mime_type(ext: str) -> str:
        mapping = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return mapping.get(ext, "application/octet-stream")

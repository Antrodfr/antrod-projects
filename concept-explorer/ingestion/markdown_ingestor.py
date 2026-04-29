"""Markdown document ingestion via direct text parsing."""

from __future__ import annotations

import re
from pathlib import Path

from ingestion.base import Document, Ingestor


class MarkdownIngestor(Ingestor):
    """Parse Markdown files into text chunks split by headings."""

    def ingest(self, file_path: str | Path) -> Document:
        path = self._validate_path(file_path)
        content = path.read_text(encoding="utf-8")

        metadata = {
            "format": "markdown",
            "filename": path.name,
            "chars": str(len(content)),
        }

        chunks = self._split_by_headings(content)
        return Document(text_chunks=chunks, images=[], metadata=metadata)

    @staticmethod
    def _split_by_headings(text: str) -> list[str]:
        """Split markdown text into chunks by headings."""
        sections: list[str] = []
        current: list[str] = []

        for line in text.split("\n"):
            if re.match(r"^#{1,6}\s", line) and current:
                section = "\n".join(current).strip()
                if section:
                    sections.append(section)
                current = [line]
            else:
                current.append(line)

        if current:
            section = "\n".join(current).strip()
            if section:
                sections.append(section)

        return sections if sections else [text.strip()] if text.strip() else []

"""Base classes and data structures for document ingestion."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    """Unified representation of an ingested document."""

    text_chunks: list[str] = field(default_factory=list)
    images: list[bytes] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.text_chunks)

    @property
    def is_empty(self) -> bool:
        return not self.text_chunks and not self.images


class Ingestor(abc.ABC):
    """Abstract base class for document ingestors."""

    @abc.abstractmethod
    def ingest(self, file_path: str | Path) -> Document:
        """Ingest a file and return a Document."""
        ...

    @staticmethod
    def _validate_path(file_path: str | Path) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return path

"""Tests for document ingestion."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from ingestion.base import Document, Ingestor
from ingestion.markdown_ingestor import MarkdownIngestor


class TestDocument(unittest.TestCase):
    """Test the Document dataclass."""

    def test_empty_document(self) -> None:
        doc = Document()
        self.assertTrue(doc.is_empty)
        self.assertEqual(doc.full_text, "")

    def test_document_with_text(self) -> None:
        doc = Document(text_chunks=["Hello", "World"])
        self.assertFalse(doc.is_empty)
        self.assertEqual(doc.full_text, "Hello\n\nWorld")

    def test_document_metadata(self) -> None:
        doc = Document(metadata={"format": "test"})
        self.assertEqual(doc.metadata["format"], "test")


class TestMarkdownIngestor(unittest.TestCase):
    """Test the Markdown ingestor."""

    def setUp(self) -> None:
        self.ingestor = MarkdownIngestor()

    def test_ingest_simple_markdown(self) -> None:
        content = "# Title\n\nSome content here.\n\n## Section 2\n\nMore content."
        fd, path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            doc = self.ingestor.ingest(path)
            self.assertFalse(doc.is_empty)
            self.assertEqual(len(doc.text_chunks), 2)
            self.assertIn("Title", doc.text_chunks[0])
            self.assertIn("Section 2", doc.text_chunks[1])
            self.assertEqual(doc.metadata["format"], "markdown")
        finally:
            os.unlink(path)

    def test_ingest_no_headings(self) -> None:
        content = "Just plain text without any headings."
        fd, path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(content)
            doc = self.ingestor.ingest(path)
            self.assertEqual(len(doc.text_chunks), 1)
            self.assertEqual(doc.text_chunks[0], content)
        finally:
            os.unlink(path)

    def test_ingest_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.ingestor.ingest("/nonexistent/path.md")

    def test_split_by_headings(self) -> None:
        text = "# H1\nContent1\n## H2\nContent2\n### H3\nContent3"
        chunks = MarkdownIngestor._split_by_headings(text)
        self.assertEqual(len(chunks), 3)

    def test_empty_file(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".md")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("")
            doc = self.ingestor.ingest(path)
            self.assertTrue(doc.is_empty)
        finally:
            os.unlink(path)


class TestIngestorRegistry(unittest.TestCase):
    """Test the ingestor registry."""

    def test_get_ingestor_markdown(self) -> None:
        from ingestion import get_ingestor

        ingestor = get_ingestor("test.md")
        self.assertIsInstance(ingestor, MarkdownIngestor)

    def test_get_ingestor_unsupported(self) -> None:
        from ingestion import get_ingestor

        with self.assertRaises(ValueError):
            get_ingestor("test.xyz")


class TestDemoLoader(unittest.TestCase):
    """Test the demo data loader."""

    def test_load_demo_graph(self) -> None:
        from demo.loader import load_demo_graph

        graph = load_demo_graph()
        self.assertGreater(len(graph.concepts), 0)
        self.assertGreater(len(graph.relationships), 0)

        # Check all concepts have explanations at all levels
        for concept in graph.concepts:
            self.assertIn("beginner", concept.explanations)
            self.assertIn("intermediate", concept.explanations)
            self.assertIn("expert", concept.explanations)
            self.assertGreater(len(concept.quiz_questions), 0)

    def test_search_concepts(self) -> None:
        from demo.loader import load_demo_graph

        graph = load_demo_graph()
        results = graph.search("encryption")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].id, "encryption")

    def test_get_related(self) -> None:
        from demo.loader import load_demo_graph

        graph = load_demo_graph()
        related = graph.get_related("zero-trust")
        self.assertGreater(len(related), 0)


if __name__ == "__main__":
    unittest.main()

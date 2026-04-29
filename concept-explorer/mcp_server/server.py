"""MCP server exposing concept-explorer tools via stdio transport."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# In-memory store for processed documents
_documents: dict[str, "ConceptGraph"] = {}  # type: ignore[name-defined]
_counter = 0


def _load_demo_graph() -> "ConceptGraph":  # type: ignore[name-defined]
    """Load the demo concept graph from sample data."""
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from demo.loader import load_demo_graph

    return load_demo_graph()


def create_server() -> "Server":  # type: ignore[name-defined]
    """Create and configure the MCP server."""
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise ImportError(
            "mcp is required for server mode: pip install -r requirements-mcp.txt"
        ) from exc

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

    from ai.models import ConceptGraph

    server = Server("concept-explorer")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="ingest_document",
                description="Ingest a document and extract concepts. Returns a document ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the document file"},
                        "format": {
                            "type": "string",
                            "description": "File format (pdf, docx, pptx, md, png, jpg)",
                            "enum": ["pdf", "docx", "pptx", "md", "png", "jpg"],
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="get_concepts",
                description="Get all concepts and relationships for a processed document.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID from ingest_document"},
                    },
                    "required": ["doc_id"],
                },
            ),
            Tool(
                name="explain_concept",
                description="Get an explanation of a concept at a given difficulty level.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string", "description": "Concept name or ID"},
                        "level": {
                            "type": "string",
                            "description": "Difficulty level",
                            "enum": ["beginner", "intermediate", "expert"],
                            "default": "beginner",
                        },
                    },
                    "required": ["concept"],
                },
            ),
            Tool(
                name="quiz",
                description="Get quiz questions for a concept.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string", "description": "Concept name or ID"},
                    },
                    "required": ["concept"],
                },
            ),
            Tool(
                name="search_concepts",
                description="Search across all loaded concepts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        global _counter

        if name == "ingest_document":
            file_path = arguments["file_path"]
            try:
                from ingestion import get_ingestor
                from ai.extractor import ConceptExtractor

                ingestor = get_ingestor(file_path)
                doc = ingestor.ingest(file_path)

                api_key = os.getenv("MISTRAL_API_KEY", "")
                if api_key:
                    extractor = ConceptExtractor(api_key=api_key)
                    graph = extractor.extract_concepts(doc.full_text)
                else:
                    graph = _load_demo_graph()

                _counter += 1
                doc_id = f"doc-{_counter}"
                _documents[doc_id] = graph

                concept_names = [c.name for c in graph.concepts]
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "doc_id": doc_id,
                        "concepts_count": len(graph.concepts),
                        "concepts": concept_names,
                    }),
                )]
            except Exception as exc:
                return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]

        elif name == "get_concepts":
            doc_id = arguments["doc_id"]
            graph = _documents.get(doc_id)
            if not graph:
                return [TextContent(type="text", text=json.dumps({"error": "Document not found"}))]
            data = {
                "concepts": [
                    {"id": c.id, "name": c.name, "category": c.category}
                    for c in graph.concepts
                ],
                "relationships": [
                    {"source": r.source, "target": r.target, "type": r.relation_type}
                    for r in graph.relationships
                ],
            }
            return [TextContent(type="text", text=json.dumps(data))]

        elif name == "explain_concept":
            concept_query = arguments["concept"].lower()
            level = arguments.get("level", "beginner")
            for graph in _documents.values():
                for c in graph.concepts:
                    if c.id == concept_query or c.name.lower() == concept_query:
                        return [TextContent(
                            type="text",
                            text=json.dumps({
                                "concept": c.name,
                                "level": level,
                                "explanation": c.get_explanation(level),
                            }),
                        )]
            return [TextContent(type="text", text=json.dumps({"error": "Concept not found"}))]

        elif name == "quiz":
            concept_query = arguments["concept"].lower()
            for graph in _documents.values():
                for c in graph.concepts:
                    if c.id == concept_query or c.name.lower() == concept_query:
                        questions = [
                            {
                                "question": q.question,
                                "choices": q.choices,
                                "correct_index": q.correct_index,
                                "explanation": q.explanation,
                            }
                            for q in c.quiz_questions
                        ]
                        return [TextContent(
                            type="text", text=json.dumps({"concept": c.name, "questions": questions})
                        )]
            return [TextContent(type="text", text=json.dumps({"error": "Concept not found"}))]

        elif name == "search_concepts":
            query = arguments["query"]
            results: list[dict] = []
            for graph in _documents.values():
                for c in graph.search(query):
                    results.append({"id": c.id, "name": c.name, "category": c.category})
            return [TextContent(type="text", text=json.dumps({"results": results}))]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return server


async def main() -> None:
    """Run the MCP server with stdio transport."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError(
            "mcp is required for server mode: pip install -r requirements-mcp.txt"
        ) from exc

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

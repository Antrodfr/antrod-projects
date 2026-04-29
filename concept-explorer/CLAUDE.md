# Concept Explorer — Dev Guide

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Demo mode loads automatically (Zero Trust example, 8 concepts) — no API key needed.

For real document ingestion: `cp .env.example .env` and add a `MISTRAL_API_KEY`.

For MCP server mode:
```bash
pip install -r requirements-mcp.txt
python -m mcp_server.server
```

## Architecture

- `app.py` — Streamlit entry point (Upload, Explorer, Quiz pages)
- `ingestion/` — 5 format-specific ingestors (PDF, DOCX, PPTX, Image, Markdown) with base class + unified `Document` dataclass
- `ai/extractor.py` — `ConceptExtractor` using Mistral API, structured JSON output
- `ai/models.py` — Dataclasses: `Concept`, `Relationship`, `ConceptGraph`
- `ai/prompts.py` — System/user prompts for concept extraction
- `visualization/graph.py` — pyvis graph builder (dark theme, color-coded categories)
- `mcp_server/server.py` — MCP server exposing 5 tools (ingest, get_concepts, explain, quiz, search)
- `demo/sample_concepts.json` — Pre-computed concepts for demo mode
- `tests/` — 13 tests for ingestion layer

## Key Design Decisions

- Multi-format ingestion via a common `Ingestor` base class returning `Document` dataclass
- 3 explanation levels per concept (Beginner / Intermediate / Expert)
- pyvis for interactive graph (vis.js under the hood, renders in Streamlit via components.html)
- MCP server uses stdio transport for Claude Desktop / Copilot integration
- Demo mode detected automatically when no API key is set

## Testing

```bash
python -m pytest tests/ -v
```

13 tests covering all ingestors.

## TODO

- [ ] Add integration tests for AI extraction (with mock API)
- [ ] Add PDF/PPTX sample files in demo/
- [ ] Add concept search/filter in the Streamlit UI
- [ ] Add export (PNG of graph, Markdown summary)
- [ ] Add multi-document support (merge concept graphs)
- [ ] Add embedding-based semantic search across concepts

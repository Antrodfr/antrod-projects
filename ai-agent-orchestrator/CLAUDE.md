# AI Agent Orchestrator — Dev Guide

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # add MISTRAL_API_KEY or OPENAI_API_KEY
python -m examples.research_workflow "your topic"
python -m examples.competitive_analysis "your topic"
```

## Architecture

- `orchestrator/agent.py` — Base `Agent` class, async `run()`, supports Mistral + OpenAI
- `orchestrator/workflow.py` — DAG-based `Workflow` engine (sequential + parallel)
- `orchestrator/tools.py` — Built-in tools: `web_search()` (DuckDuckGo), `summarize()`
- `orchestrator/config.py` — Env-var config via python-dotenv
- `examples/` — Two ready-to-run workflows (research pipeline, competitive analysis fan-out)

## Key Design Decisions

- Async-first (`asyncio`) for parallel agent execution
- No heavy framework dependency (no LangChain/CrewAI) — lightweight by design
- Agents are composable: each has a role, model, and system prompt
- Workflows define execution order via a simple DAG (nodes + edges)

## Testing

No test suite yet. To validate, run the examples and check output quality.

## TODO

- [ ] Add unit tests for workflow DAG resolution
- [ ] Add streaming output support
- [ ] Add tool-use (function calling) within agents
- [ ] Add retry/fallback logic on API failures
- [ ] Add a CLI entry point

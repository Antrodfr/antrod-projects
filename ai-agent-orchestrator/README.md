<div align="center">

# 🤖 AI Agent Orchestrator

**A lightweight Python framework for orchestrating multi-agent AI workflows**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Mistral AI](https://img.shields.io/badge/Mistral-AI-orange.svg)](https://mistral.ai/)
[![OpenAI](https://img.shields.io/badge/OpenAI-compatible-green.svg)](https://openai.com/)
[![asyncio](https://img.shields.io/badge/async-await-purple.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

Chain specialized AI agents — researcher, analyzer, synthesizer — into sequential or parallel workflows. Built to explore multi-agent architectures with minimal abstraction.

## Architecture

```
                          ┌─────────────────────────────────┐
                          │         Workflow Engine          │
                          │   (DAG-based step execution)    │
                          └──────────┬──────────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
          ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
          │  Researcher  │    │  Analyzer   │    │ Synthesizer │
          │    Agent     │    │    Agent    │    │    Agent    │
          └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
                 │                   │                   │
          ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
          │   Tools      │    │   Tools     │    │   Tools     │
          │ (search,     │    │ (summarize) │    │ (summarize) │
          │  summarize)  │    │             │    │             │
          └─────────────┘    └─────────────┘    └─────────────┘
                 │                   │                   │
                 └───────────────────┼───────────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │   LLM Provider      │
                          │ (Mistral / OpenAI)  │
                          └─────────────────────┘


  Sequential:   [Agent A] ──► [Agent B] ──► [Agent C]

  Fan-out/in:   [Agent A] ──┬──► [Agent B1] ──┬──► [Agent C]
                            ├──► [Agent B2] ──┤
                            └──► [Agent B3] ──┘
```

## Quick Start

```bash
# Clone and install
git clone https://github.com/yourusername/ai-agent-orchestrator.git
cd ai-agent-orchestrator
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API key to .env

# Run the research pipeline example
python -m examples.research_workflow "Impact of AI on product management"
```

## Usage

### Define agents and chain them into a workflow

```python
import asyncio
from orchestrator import Agent, Workflow

researcher = Agent(
    name="Researcher",
    role="Generate search queries and key questions about a topic.",
    provider="mistral",
)

analyzer = Agent(
    name="Analyzer",
    role="Identify patterns and insights from research notes.",
    provider="mistral",
)

synthesizer = Agent(
    name="Synthesizer",
    role="Produce a structured executive summary.",
    provider="mistral",
)

workflow = Workflow(name="Research Pipeline")
step1 = workflow.add_step(researcher)
step2 = workflow.add_step(analyzer, depends_on=[step1])
step3 = workflow.add_step(synthesizer, depends_on=[step2])

result = asyncio.run(workflow.execute("How is AI changing healthcare?"))
print(result.final_output)
```

### Parallel fan-out / fan-in

```python
workflow = Workflow(name="Competitive Analysis")

# Fan-out: run analysts in parallel
analysts = [
    workflow.add_step(Agent(name=f"Analyst-{c}", role=f"Analyze {c}'s strategy."))
    for c in ["Competitor A", "Competitor B", "Competitor C"]
]

# Fan-in: synthesize all analyses
workflow.add_step(strategist, depends_on=analysts)
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `MISTRAL_API_KEY` | Mistral AI API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `DEFAULT_PROVIDER` | `mistral` or `openai` | `mistral` |
| `DEFAULT_MODEL` | Model identifier | `mistral-small-latest` |

## Project Structure

```
ai-agent-orchestrator/
├── orchestrator/
│   ├── __init__.py        # Public API exports
│   ├── agent.py           # Base Agent class (Mistral & OpenAI)
│   ├── workflow.py         # Workflow engine with DAG execution
│   ├── tools.py           # Web search & summarize helpers
│   └── config.py          # Environment-based configuration
├── examples/
│   ├── research_workflow.py       # Sequential 3-agent pipeline
│   └── competitive_analysis.py   # Parallel fan-out/fan-in
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).

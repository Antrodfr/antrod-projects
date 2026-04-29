"""Sequential 3-agent research pipeline.

Usage:
    python -m examples.research_workflow "Impact of AI on product management"
"""

from __future__ import annotations

import asyncio
import logging
import sys

from orchestrator import Agent, Workflow

logging.basicConfig(level=logging.INFO, format="%(message)s")


def build_pipeline() -> Workflow:
    """Construct a Researcher → Analyzer → Synthesizer pipeline."""

    researcher = Agent(
        name="Researcher",
        role=(
            "You are a senior research analyst. Given a topic, generate:\n"
            "1. Five targeted search queries to investigate the topic.\n"
            "2. Five key questions that must be answered.\n"
            "3. A brief landscape summary of what is publicly known."
        ),
    )

    analyzer = Agent(
        name="Analyzer",
        role=(
            "You are a strategic analyst. Given research notes, identify:\n"
            "1. Three major patterns or trends.\n"
            "2. Two non-obvious insights.\n"
            "3. Key risks or open questions.\n"
            "Be concrete and cite specifics from the input."
        ),
    )

    synthesizer = Agent(
        name="Synthesizer",
        role=(
            "You are an executive communication specialist. Given an analysis, "
            "produce a structured executive summary with:\n"
            "- One-paragraph TL;DR\n"
            "- Key findings (bullet points)\n"
            "- Strategic recommendations\n"
            "- Suggested next steps\n"
            "Keep it under 400 words."
        ),
    )

    wf = Workflow(name="Research Pipeline")
    s1 = wf.add_step(researcher)
    s2 = wf.add_step(analyzer, depends_on=[s1])
    wf.add_step(synthesizer, depends_on=[s2])
    return wf


async def main(topic: str) -> None:
    wf = build_pipeline()
    result = await wf.execute(topic)

    print("\n" + "=" * 60)
    print(result.summary())
    print("=" * 60)
    for step in result.steps:
        print(f"\n── {step.agent_name} ({step.duration_s:.1f}s) ──")
        print(step.output_text)


if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) or "Impact of AI on product management"
    asyncio.run(main(topic))

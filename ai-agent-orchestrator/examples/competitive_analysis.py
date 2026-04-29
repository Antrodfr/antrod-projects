"""Parallel fan-out / fan-in competitive analysis workflow.

Usage:
    python -m examples.competitive_analysis
"""

from __future__ import annotations

import asyncio
import logging

from orchestrator import Agent, Workflow

logging.basicConfig(level=logging.INFO, format="%(message)s")

COMPETITORS = ["Notion", "Coda", "Airtable"]


def build_competitive_workflow(competitors: list[str]) -> Workflow:
    """Build a fan-out/fan-in workflow: one analyst per competitor, one strategist."""

    wf = Workflow(name="Competitive Analysis")

    analyst_steps: list[str] = []
    for company in competitors:
        analyst = Agent(
            name=f"Analyst-{company}",
            role=(
                f"You are a competitive intelligence analyst specializing in {company}. "
                "Given a market context, produce a concise competitive profile:\n"
                "- Company positioning and key value proposition\n"
                "- Recent product moves and strategic bets\n"
                "- Strengths and weaknesses\n"
                "- Threat level (low / medium / high) with reasoning"
            ),
        )
        step_id = wf.add_step(analyst)
        analyst_steps.append(step_id)

    strategist = Agent(
        name="Strategist",
        role=(
            "You are a VP of Strategy. Given competitive profiles for multiple "
            "companies, synthesize a unified strategic brief:\n"
            "- Competitive landscape overview\n"
            "- Where we are differentiated vs. vulnerable\n"
            "- Three recommended strategic moves\n"
            "- Priority actions for the next quarter\n"
            "Keep it under 500 words."
        ),
    )
    wf.add_step(strategist, depends_on=analyst_steps)
    return wf


async def main() -> None:
    wf = build_competitive_workflow(COMPETITORS)
    context = (
        "We are building a collaborative workspace tool for product teams. "
        "Our differentiator is native AI agent integration for automated research, "
        "decision logging, and stakeholder updates."
    )
    result = await wf.execute(context)

    print("\n" + "=" * 60)
    print(result.summary())
    print("=" * 60)
    for step in result.steps:
        print(f"\n── {step.agent_name} ({step.duration_s:.1f}s) ──")
        print(step.output_text)


if __name__ == "__main__":
    asyncio.run(main())

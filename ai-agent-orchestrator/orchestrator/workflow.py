"""DAG-based workflow engine for chaining agents."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from orchestrator.agent import Agent

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """Output of a single workflow step."""

    step_id: str
    agent_name: str
    input_text: str
    output_text: str
    duration_s: float


@dataclass
class WorkflowResult:
    """Aggregate result of a complete workflow execution."""

    steps: list[StepResult] = field(default_factory=list)

    @property
    def final_output(self) -> str:
        """Return the output of the last completed step."""
        return self.steps[-1].output_text if self.steps else ""

    def summary(self) -> str:
        """Return a human-readable execution summary."""
        lines = [f"Workflow completed in {len(self.steps)} step(s):\n"]
        for s in self.steps:
            lines.append(f"  • {s.agent_name} ({s.duration_s:.1f}s)")
        return "\n".join(lines)


@dataclass
class _Step:
    """Internal representation of a workflow node."""

    id: str
    agent: Agent
    depends_on: list[str] = field(default_factory=list)


class Workflow:
    """Orchestrate agents as a directed acyclic graph (DAG).

    Steps with no dependencies run in parallel.  A step that depends on
    multiple parents receives their outputs concatenated as its input.

    Example::

        wf = Workflow("demo")
        s1 = wf.add_step(agent_a)
        s2 = wf.add_step(agent_b, depends_on=[s1])
        result = await wf.execute("initial prompt")
    """

    def __init__(self, name: str = "workflow") -> None:
        self.name = name
        self._steps: dict[str, _Step] = {}
        self._counter: int = 0

    # ── building the DAG ─────────────────────────────────────

    def add_step(
        self,
        agent: Agent,
        depends_on: list[str] | None = None,
    ) -> str:
        """Add an agent as a workflow step.

        Args:
            agent: The agent to execute at this step.
            depends_on: List of step IDs that must complete first.
                        ``None`` means the step receives the initial input.

        Returns:
            A unique step ID.
        """
        self._counter += 1
        step_id = f"step-{self._counter}"
        self._steps[step_id] = _Step(
            id=step_id,
            agent=agent,
            depends_on=depends_on or [],
        )
        return step_id

    # ── execution ────────────────────────────────────────────

    async def execute(self, initial_input: str) -> WorkflowResult:
        """Run the full workflow and return aggregated results."""
        logger.info("▶ Starting workflow '%s'", self.name)

        result = WorkflowResult()
        outputs: dict[str, str] = {}  # step_id → output
        completed: set[str] = set()

        while len(completed) < len(self._steps):
            ready = [
                s for s in self._steps.values()
                if s.id not in completed
                and all(d in completed for d in s.depends_on)
            ]
            if not ready:
                raise RuntimeError("Cycle detected or unresolvable dependencies.")

            tasks = []
            for step in ready:
                step_input = self._resolve_input(step, outputs, initial_input)
                tasks.append(self._run_step(step, step_input))

            step_results = await asyncio.gather(*tasks)

            for sr in step_results:
                outputs[sr.step_id] = sr.output_text
                completed.add(sr.step_id)
                result.steps.append(sr)

        logger.info("✓ Workflow '%s' finished", self.name)
        return result

    # ── internals ────────────────────────────────────────────

    @staticmethod
    def _resolve_input(
        step: _Step,
        outputs: dict[str, str],
        initial_input: str,
    ) -> str:
        """Build the input for a step from its parents' outputs."""
        if not step.depends_on:
            return initial_input
        parts = [outputs[dep] for dep in step.depends_on]
        return "\n\n---\n\n".join(parts)

    @staticmethod
    async def _run_step(step: _Step, input_text: str) -> StepResult:
        """Execute a single step and capture timing."""
        start = time.perf_counter()
        output = await step.agent.run(input_text)
        duration = time.perf_counter() - start
        logger.info("[%s] completed in %.1fs", step.agent.name, duration)
        return StepResult(
            step_id=step.id,
            agent_name=step.agent.name,
            input_text=input_text,
            output_text=output,
            duration_s=round(duration, 2),
        )

"""Demo data loader for concept-explorer."""

from __future__ import annotations

import json
from pathlib import Path

from ai.models import Concept, ConceptGraph, QuizQuestion, Relationship

DEMO_DIR = Path(__file__).resolve().parent


def load_demo_graph() -> ConceptGraph:
    """Load the pre-computed demo concept graph from sample_concepts.json."""
    json_path = DEMO_DIR / "sample_concepts.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Demo data not found: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    concepts: list[Concept] = []
    for c in data["concepts"]:
        quiz_questions = [
            QuizQuestion(
                question=q["question"],
                choices=q["choices"],
                correct_index=q["correct_index"],
                explanation=q.get("explanation", ""),
            )
            for q in c.get("quiz_questions", [])
        ]
        concepts.append(
            Concept(
                id=c["id"],
                name=c["name"],
                category=c.get("category", ""),
                source_excerpt=c.get("source_excerpt", ""),
                explanations=c.get("explanations", {}),
                quiz_questions=quiz_questions,
            )
        )

    relationships = [
        Relationship(
            source=r["source"],
            target=r["target"],
            relation_type=r.get("relation_type", "related"),
            label=r.get("label", ""),
        )
        for r in data.get("relationships", [])
    ]

    return ConceptGraph(concepts=concepts, relationships=relationships)


def load_demo_document_text() -> str:
    """Load the demo markdown document text."""
    md_path = DEMO_DIR / "sample_zero_trust.md"
    if not md_path.exists():
        raise FileNotFoundError(f"Demo document not found: {md_path}")
    return md_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    graph = load_demo_graph()
    print(f"Loaded {len(graph.concepts)} concepts, {len(graph.relationships)} relationships")
    for c in graph.concepts:
        print(f"  - {c.name} ({c.category})")

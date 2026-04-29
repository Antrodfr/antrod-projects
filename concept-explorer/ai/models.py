"""Data models for the concept extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class RelationshipType(str, Enum):
    PREREQUISITE = "prerequisite"
    RELATED = "related"
    PART_OF = "part-of"


@dataclass
class QuizQuestion:
    """A multiple-choice quiz question about a concept."""

    question: str
    choices: list[str]
    correct_index: int
    explanation: str = ""

    @property
    def correct_answer(self) -> str:
        return self.choices[self.correct_index]


@dataclass
class Concept:
    """A single concept extracted from a document."""

    id: str
    name: str
    category: str = ""
    source_excerpt: str = ""
    explanations: dict[str, str] = field(default_factory=dict)
    quiz_questions: list[QuizQuestion] = field(default_factory=list)

    def get_explanation(self, level: str = "beginner") -> str:
        return self.explanations.get(level, "No explanation available.")


@dataclass
class Relationship:
    """A directed relationship between two concepts."""

    source: str  # concept id
    target: str  # concept id
    relation_type: str = "related"
    label: str = ""


@dataclass
class ConceptGraph:
    """A graph of concepts and their relationships."""

    concepts: list[Concept] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def get_concept(self, concept_id: str) -> Concept | None:
        for c in self.concepts:
            if c.id == concept_id:
                return c
        return None

    def get_related(self, concept_id: str) -> list[tuple[Concept, str]]:
        """Return concepts related to the given concept with relationship type."""
        related: list[tuple[Concept, str]] = []
        for rel in self.relationships:
            other_id = None
            if rel.source == concept_id:
                other_id = rel.target
            elif rel.target == concept_id:
                other_id = rel.source
            if other_id:
                concept = self.get_concept(other_id)
                if concept:
                    related.append((concept, rel.relation_type))
        return related

    @property
    def categories(self) -> list[str]:
        return sorted({c.category for c in self.concepts if c.category})

    def search(self, query: str) -> list[Concept]:
        """Simple text search across concept names and explanations."""
        query_lower = query.lower()
        results: list[Concept] = []
        for concept in self.concepts:
            if query_lower in concept.name.lower():
                results.append(concept)
                continue
            for explanation in concept.explanations.values():
                if query_lower in explanation.lower():
                    results.append(concept)
                    break
        return results

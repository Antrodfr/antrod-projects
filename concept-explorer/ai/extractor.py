"""Concept extraction using Mistral AI API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from ai.models import Concept, ConceptGraph, QuizQuestion, Relationship
from ai.prompts import (
    CONCEPT_EXTRACTION_PROMPT,
    EXPLANATION_PROMPT,
    QUIZ_PROMPT,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)


class ConceptExtractor:
    """Extract concepts from text using the Mistral AI API."""

    def __init__(self, api_key: str | None = None, model: str = "mistral-small-latest") -> None:
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY", "")
        self.model = model
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                from mistralai import Mistral
            except ImportError as exc:
                raise ImportError("mistralai is required: pip install mistralai") from exc
            if not self.api_key:
                raise ValueError("MISTRAL_API_KEY is required for AI extraction.")
            self._client = Mistral(api_key=self.api_key)
        return self._client

    def _call_api(self, user_prompt: str) -> str:
        """Make a synchronous call to the Mistral API."""
        response = self.client.chat.complete(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    async def _call_api_async(self, user_prompt: str) -> str:
        """Make an async call to the Mistral API."""
        response = await self.client.chat.complete_async(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return content if isinstance(content, str) else str(content)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """Safely parse JSON from API response."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                return json.loads(match.group(1))
            raise

    def extract_concepts(self, text: str) -> ConceptGraph:
        """Extract concepts and relationships from text (synchronous)."""
        prompt = CONCEPT_EXTRACTION_PROMPT.format(text=text[:8000])
        raw = self._call_api(prompt)
        data = self._parse_json(raw)
        return self._build_graph(data, text)

    async def extract_concepts_async(self, text: str) -> ConceptGraph:
        """Extract concepts and relationships from text (async)."""
        prompt = CONCEPT_EXTRACTION_PROMPT.format(text=text[:8000])
        raw = await self._call_api_async(prompt)
        data = self._parse_json(raw)
        return await self._build_graph_async(data, text)

    def _build_graph(self, data: dict[str, Any], context: str) -> ConceptGraph:
        """Build a ConceptGraph with explanations and quizzes."""
        concepts: list[Concept] = []
        for c in data.get("concepts", []):
            concept = Concept(
                id=c["id"],
                name=c["name"],
                category=c.get("category", ""),
                source_excerpt=c.get("source_excerpt", ""),
            )
            # Fetch explanations
            try:
                expl_raw = self._call_api(
                    EXPLANATION_PROMPT.format(concept_name=concept.name, context=context[:3000])
                )
                concept.explanations = self._parse_json(expl_raw)
            except Exception as exc:
                logger.warning("Failed to get explanations for %s: %s", concept.name, exc)
                concept.explanations = {
                    "beginner": f"{concept.name} is a key concept in this document.",
                    "intermediate": f"{concept.name}: {concept.source_excerpt}",
                    "expert": f"{concept.name}: {concept.source_excerpt}",
                }

            # Fetch quiz questions
            try:
                quiz_raw = self._call_api(
                    QUIZ_PROMPT.format(concept_name=concept.name, context=context[:3000])
                )
                quiz_data = self._parse_json(quiz_raw)
                concept.quiz_questions = [
                    QuizQuestion(**q) for q in quiz_data.get("questions", [])
                ]
            except Exception as exc:
                logger.warning("Failed to get quiz for %s: %s", concept.name, exc)

            concepts.append(concept)

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

    async def _build_graph_async(self, data: dict[str, Any], context: str) -> ConceptGraph:
        """Build a ConceptGraph with async API calls for explanations and quizzes."""
        concepts_raw = data.get("concepts", [])

        async def enrich_concept(c: dict[str, Any]) -> Concept:
            concept = Concept(
                id=c["id"],
                name=c["name"],
                category=c.get("category", ""),
                source_excerpt=c.get("source_excerpt", ""),
            )
            try:
                expl_raw = await self._call_api_async(
                    EXPLANATION_PROMPT.format(concept_name=concept.name, context=context[:3000])
                )
                concept.explanations = self._parse_json(expl_raw)
            except Exception as exc:
                logger.warning("Failed to get explanations for %s: %s", concept.name, exc)
                concept.explanations = {
                    "beginner": f"{concept.name} is a key concept in this document.",
                    "intermediate": f"{concept.name}: {concept.source_excerpt}",
                    "expert": f"{concept.name}: {concept.source_excerpt}",
                }
            try:
                quiz_raw = await self._call_api_async(
                    QUIZ_PROMPT.format(concept_name=concept.name, context=context[:3000])
                )
                quiz_data = self._parse_json(quiz_raw)
                concept.quiz_questions = [
                    QuizQuestion(**q) for q in quiz_data.get("questions", [])
                ]
            except Exception as exc:
                logger.warning("Failed to get quiz for %s: %s", concept.name, exc)
            return concept

        concepts = await asyncio.gather(*[enrich_concept(c) for c in concepts_raw])

        relationships = [
            Relationship(
                source=r["source"],
                target=r["target"],
                relation_type=r.get("relation_type", "related"),
                label=r.get("label", ""),
            )
            for r in data.get("relationships", [])
        ]

        return ConceptGraph(concepts=list(concepts), relationships=relationships)

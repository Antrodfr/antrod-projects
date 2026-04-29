"""Prompt templates for Mistral AI concept extraction."""

SYSTEM_PROMPT = """You are an expert educator and knowledge graph builder. Your task is to analyze \
text and extract key concepts, their relationships, and generate explanations at multiple levels.

Always respond with valid JSON matching the requested schema. Be thorough but concise."""

CONCEPT_EXTRACTION_PROMPT = """Analyze the following text and extract the key concepts.

TEXT:
{text}

Return a JSON object with this exact structure:
{{
  "concepts": [
    {{
      "id": "lowercase-hyphenated-id",
      "name": "Human Readable Name",
      "category": "general category",
      "source_excerpt": "brief relevant excerpt from the text"
    }}
  ],
  "relationships": [
    {{
      "source": "concept-id-1",
      "target": "concept-id-2",
      "relation_type": "prerequisite|related|part-of",
      "label": "brief description of relationship"
    }}
  ]
}}

Extract 5-15 key concepts. Include meaningful relationships between them.
Relationship types: "prerequisite" (A is needed to understand B), "related" (A and B are related), \
"part-of" (A is a component of B)."""

EXPLANATION_PROMPT = """Generate explanations for the concept "{concept_name}" in the context of:
{context}

Return a JSON object:
{{
  "beginner": "Simple ELI5 explanation (2-3 sentences, no jargon)",
  "intermediate": "Clear explanation for someone with basic knowledge (3-4 sentences)",
  "expert": "Technical, detailed explanation for professionals (4-5 sentences)"
}}"""

QUIZ_PROMPT = """Generate 2 multiple-choice quiz questions about "{concept_name}".

Context: {context}

Return a JSON object:
{{
  "questions": [
    {{
      "question": "The question text",
      "choices": ["Option A", "Option B", "Option C", "Option D"],
      "correct_index": 0,
      "explanation": "Why the correct answer is correct"
    }}
  ]
}}"""

"""Simple tools that agents can invoke."""

from __future__ import annotations

import httpx


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web via DuckDuckGo Instant Answer API (no key required).

    Returns a plain-text summary of results.
    """
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_redirect": "1"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    results: list[str] = []
    if data.get("AbstractText"):
        results.append(data["AbstractText"])
    for topic in data.get("RelatedTopics", [])[:max_results]:
        if "Text" in topic:
            results.append(topic["Text"])

    return "\n".join(results) if results else f"No results found for: {query}"


def summarize(text: str, max_words: int = 150) -> str:
    """Truncate text to approximately *max_words* words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"

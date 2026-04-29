"""Lightweight GitHub REST API client using httpx."""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import httpx
import pandas as pd

BASE_URL = "https://api.github.com"


def _headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    h: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _get(url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """GET with basic pagination and rate-limit back-off."""
    items: list[dict[str, Any]] = []
    params = params or {}
    params.setdefault("per_page", 100)
    page = 1

    while True:
        params["page"] = page
        resp = httpx.get(url, headers=_headers(), params=params, timeout=30)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait = max(1, reset - int(time.time()))
            time.sleep(wait)
            continue

        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        items.extend(batch)
        page += 1

    return items


def fetch_pull_requests(
    owner: str,
    repo: str,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Fetch merged pull requests and return a normalised DataFrame."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
    params: dict[str, Any] = {"state": "closed", "sort": "updated", "direction": "desc"}
    raw = _get(url, params)

    rows: list[dict[str, Any]] = []
    for pr in raw:
        merged = pr.get("merged_at")
        if not merged:
            continue
        merged_dt = datetime.fromisoformat(merged.replace("Z", "+00:00"))
        if since and merged_dt < since:
            continue
        rows.append({
            "number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "created_at": datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00")),
            "merged_at": merged_dt,
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
        })

    return pd.DataFrame(rows)


def fetch_commits(
    owner: str,
    repo: str,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Fetch commits for the default branch."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
    params: dict[str, Any] = {}
    if since:
        params["since"] = since.isoformat()
    raw = _get(url, params)

    rows = [
        {
            "sha": c["sha"],
            "author": (c.get("author") or {}).get("login", "unknown"),
            "timestamp": datetime.fromisoformat(
                c["commit"]["author"]["date"].replace("Z", "+00:00")
            ),
        }
        for c in raw
    ]
    return pd.DataFrame(rows)


def fetch_reviews(
    owner: str,
    repo: str,
    pr_number: int,
) -> list[dict[str, Any]]:
    """Fetch review records for a single PR."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    return _get(url)

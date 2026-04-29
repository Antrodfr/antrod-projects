"""Generates realistic demo data for the engineering dashboard."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

TEAM_MEMBERS: list[str] = [
    "Alice Chen", "Bob Martinez", "Clara Johansson",
    "David Kim", "Elena Petrova", "Frank Otieno",
    "Grace Nakamura", "Hassan Ali",
]

PR_PREFIXES: list[str] = [
    "feat:", "fix:", "refactor:", "chore:", "docs:", "test:", "perf:",
]

PR_SUBJECTS: list[str] = [
    "update authentication flow", "add retry logic to API client",
    "migrate database schema v3", "improve search performance",
    "fix flaky integration test", "add unit tests for billing",
    "refactor notification service", "update CI pipeline config",
    "add dark-mode support", "implement rate limiter",
    "optimize image pipeline", "fix timezone handling",
    "add export-to-CSV feature", "bump dependencies",
    "improve error messages", "add health-check endpoint",
]

SPRINT_NAMES: list[str] = [
    "Sprint {n}" for n in range(1, 14)
]


def _business_hour_jitter(base: datetime, rng: random.Random) -> datetime:
    """Shift a timestamp toward business hours with realistic noise."""
    hour = rng.gauss(14, 3)
    hour = max(8, min(22, hour))
    return base.replace(hour=int(hour), minute=rng.randint(0, 59))


def generate_pr_data(
    months: int = 6,
    seed: int = 42,
) -> pd.DataFrame:
    """Return a DataFrame of realistic pull-request records."""
    rng = random.Random(seed)
    now = datetime.now().replace(second=0, microsecond=0)
    start = now - timedelta(days=months * 30)
    records: list[dict[str, Any]] = []

    day = start
    pr_number = 100
    while day <= now:
        weekday = day.weekday()
        # Fewer PRs on weekends and Mondays
        if weekday >= 5:
            base_count = rng.randint(0, 1)
        elif weekday == 0:
            base_count = rng.randint(1, 3)
        else:
            base_count = rng.randint(2, 5)

        # Holiday-season slowdown (late Dec)
        if day.month == 12 and day.day >= 20:
            base_count = max(0, base_count - 2)

        for _ in range(base_count):
            author = rng.choice(TEAM_MEMBERS)
            reviewer = rng.choice([m for m in TEAM_MEMBERS if m != author])
            title = f"{rng.choice(PR_PREFIXES)} {rng.choice(PR_SUBJECTS)}"

            created = _business_hour_jitter(day, rng)
            review_hours = max(0.5, rng.gauss(8, 6))
            reviewed_at = created + timedelta(hours=review_hours)
            merge_hours = review_hours + max(0.25, rng.gauss(3, 2))
            merged_at = created + timedelta(hours=merge_hours)

            additions = max(1, int(rng.gauss(120, 100)))
            deletions = max(0, int(rng.gauss(40, 50)))

            records.append({
                "number": pr_number,
                "title": title,
                "author": author,
                "reviewer": reviewer,
                "created_at": created,
                "first_review_at": reviewed_at,
                "merged_at": merged_at,
                "additions": additions,
                "deletions": deletions,
                "review_comments": max(0, int(rng.gauss(2, 2))),
                "approved": rng.random() < 0.92,
            })
            pr_number += 1

        day += timedelta(days=1)

    return pd.DataFrame(records)


def generate_commit_data(
    pr_df: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    """Derive commit records from PR data with author-weight skew."""
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []

    for _, pr in pr_df.iterrows():
        n_commits = rng.randint(1, 6)
        for i in range(n_commits):
            ts = pr["created_at"] + timedelta(
                hours=rng.uniform(0, (pr["merged_at"] - pr["created_at"]).total_seconds() / 3600),
            )
            after_hours = ts.hour < 9 or ts.hour >= 18 or ts.weekday() >= 5
            records.append({
                "sha": f"{pr['number']:04d}-{i:02d}",
                "author": pr["author"],
                "timestamp": ts,
                "pr_number": pr["number"],
                "after_hours": after_hours,
            })

    return pd.DataFrame(records)


def generate_sprint_data(
    pr_df: pd.DataFrame,
    sprint_length_days: int = 14,
    seed: int = 42,
) -> pd.DataFrame:
    """Aggregate PRs into sprints with story-point estimates."""
    rng = random.Random(seed)
    min_date = pr_df["created_at"].min()
    max_date = pr_df["merged_at"].max()

    sprints: list[dict[str, Any]] = []
    sprint_start = min_date
    idx = 0
    while sprint_start < max_date:
        sprint_end = sprint_start + timedelta(days=sprint_length_days)
        mask = (pr_df["merged_at"] >= sprint_start) & (pr_df["merged_at"] < sprint_end)
        completed = int(mask.sum())
        wip = rng.randint(2, 6)
        planned = completed + wip + rng.randint(0, 3)
        points = sum(rng.choice([1, 2, 3, 5, 8]) for _ in range(completed))

        sprints.append({
            "sprint": f"Sprint {idx + 1}",
            "start": sprint_start,
            "end": sprint_end,
            "planned_items": planned,
            "completed_items": completed,
            "wip_items": wip,
            "story_points": points,
        })
        sprint_start = sprint_end
        idx += 1

    return pd.DataFrame(sprints)

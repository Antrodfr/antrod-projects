"""Pure metric-calculation functions.

Every function accepts a pandas DataFrame and returns a DataFrame or Series,
making them easy to test independently of the data source.
"""

from __future__ import annotations

import pandas as pd


def calculate_cycle_time(prs: pd.DataFrame) -> pd.Series:
    """Hours from PR creation to merge, indexed by merged_at date."""
    df = prs.dropna(subset=["merged_at"]).copy()
    df["cycle_hours"] = (
        (df["merged_at"] - df["created_at"]).dt.total_seconds() / 3600
    )
    return df.set_index("merged_at")["cycle_hours"].sort_index()


def calculate_throughput(
    prs: pd.DataFrame,
    freq: str = "W",
) -> pd.Series:
    """Count of merged PRs per time bucket."""
    merged = prs.dropna(subset=["merged_at"]).copy()
    merged["period"] = merged["merged_at"].dt.to_period(freq)
    return merged.groupby("period").size().rename("prs_merged")


def calculate_review_turnaround(prs: pd.DataFrame) -> pd.Series:
    """Hours from PR creation to first review."""
    df = prs.dropna(subset=["first_review_at"]).copy()
    df["review_hours"] = (
        (df["first_review_at"] - df["created_at"]).dt.total_seconds() / 3600
    )
    return df.set_index("created_at")["review_hours"].sort_index()


def calculate_bus_factor(commits: pd.DataFrame) -> dict[str, int]:
    """Commit count per author — a proxy for knowledge distribution."""
    return commits["author"].value_counts().to_dict()


def calculate_pr_size_distribution(prs: pd.DataFrame) -> pd.Series:
    """Total lines changed (additions + deletions) per PR."""
    return (prs["additions"] + prs["deletions"]).rename("lines_changed")


def calculate_review_coverage(prs: pd.DataFrame) -> float:
    """Fraction of PRs that received at least one review comment or approval."""
    reviewed = prs["approved"] | (prs["review_comments"] > 0)
    return float(reviewed.mean())


def calculate_after_hours_ratio(commits: pd.DataFrame) -> float:
    """Fraction of commits made outside 09:00-18:00 or on weekends."""
    return float(commits["after_hours"].mean())


def calculate_lead_time_per_sprint(
    prs: pd.DataFrame,
    sprints: pd.DataFrame,
) -> pd.DataFrame:
    """Median cycle time per sprint."""
    rows = []
    for _, sp in sprints.iterrows():
        mask = (prs["merged_at"] >= sp["start"]) & (prs["merged_at"] < sp["end"])
        subset = prs.loc[mask]
        if subset.empty:
            median_hours = 0.0
        else:
            median_hours = float(
                (subset["merged_at"] - subset["created_at"])
                .dt.total_seconds()
                .median()
                / 3600
            )
        rows.append({"sprint": sp["sprint"], "median_lead_time_hours": median_hours})
    return pd.DataFrame(rows)

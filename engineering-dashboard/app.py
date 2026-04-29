"""Engineering Dashboard — Streamlit application entry-point."""

from __future__ import annotations

from datetime import datetime, timedelta

import plotly.express as px
import streamlit as st

from data.demo_data import generate_commit_data, generate_pr_data, generate_sprint_data
from metrics import (
    calculate_after_hours_ratio,
    calculate_bus_factor,
    calculate_cycle_time,
    calculate_lead_time_per_sprint,
    calculate_pr_size_distribution,
    calculate_review_coverage,
    calculate_review_turnaround,
    calculate_throughput,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Engineering Dashboard", page_icon="📊", layout="wide")

PLOTLY_LAYOUT = dict(
    template="plotly_dark",
    margin=dict(l=40, r=20, t=40, b=30),
    height=320,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Engineering Dashboard")
data_source = st.sidebar.radio("Data source", ["Demo data", "GitHub API"], index=0)

if data_source == "GitHub API":
    owner = st.sidebar.text_input("Owner", "")
    repo = st.sidebar.text_input("Repository", "")
else:
    owner, repo = "demo", "demo-repo"
    st.sidebar.markdown(f"**Team:** `{owner}/{repo}`")

months = st.sidebar.slider("History (months)", 1, 12, 6)
since = datetime.now() - timedelta(days=months * 30)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading data …")
def load_demo(months: int) -> tuple:
    prs = generate_pr_data(months=months)
    commits = generate_commit_data(prs)
    sprints = generate_sprint_data(prs)
    return prs, commits, sprints


if data_source == "Demo data":
    prs, commits, sprints = load_demo(months)
else:
    from github_client import fetch_commits, fetch_pull_requests

    if not owner or not repo:
        st.warning("Enter an owner and repository name in the sidebar.")
        st.stop()
    with st.spinner("Fetching from GitHub …"):
        prs = fetch_pull_requests(owner, repo, since)
        commits = fetch_commits(owner, repo, since)
        if prs.empty:
            st.error("No merged PRs found for that repo / date range.")
            st.stop()
        # Fill columns expected by metrics layer
        for col in ("first_review_at", "review_comments", "approved"):
            if col not in prs.columns:
                prs[col] = None
        if "after_hours" not in commits.columns:
            commits["after_hours"] = commits["timestamp"].apply(
                lambda t: t.hour < 9 or t.hour >= 18 or t.weekday() >= 5,
            )
        sprints = generate_sprint_data(prs)

# ---------------------------------------------------------------------------
# Header KPIs
# ---------------------------------------------------------------------------
st.title("Engineering Dashboard")
st.caption(f"Showing **{len(prs)}** PRs and **{len(commits)}** commits since {since:%Y-%m-%d}")

k1, k2, k3, k4 = st.columns(4)
cycle = calculate_cycle_time(prs)
k1.metric("Median cycle time", f"{cycle.median():.1f} h")
k2.metric("PRs merged / week", f"{calculate_throughput(prs).mean():.1f}")
k3.metric("Review coverage", f"{calculate_review_coverage(prs):.0%}")
k4.metric("After-hours ratio", f"{calculate_after_hours_ratio(commits):.0%}")

st.divider()

# ===== Section 1: Delivery Velocity ========================================
st.header("🚀 Delivery Velocity")
v1, v2 = st.columns(2)

with v1:
    throughput = calculate_throughput(prs).reset_index()
    throughput["period"] = throughput["period"].astype(str)
    fig = px.bar(throughput, x="period", y="prs_merged", title="PRs Merged per Week", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

with v2:
    ct = cycle.resample("W").median().reset_index()
    ct.columns = ["week", "median_hours"]
    fig = px.line(ct, x="week", y="median_hours", title="Avg Cycle Time (hours)", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

release_count = prs.set_index("merged_at").resample("ME").size()
fig = px.bar(
    release_count.reset_index(),
    x="merged_at",
    y=0,
    title="Release Frequency (merges / month)",
    labels={"0": "merges"},
    **PLOTLY_LAYOUT,
)
st.plotly_chart(fig, use_container_width=True)

# ===== Section 2: Code Quality =============================================
st.header("🔍 Code Quality")
q1, q2 = st.columns(2)

with q1:
    rt = calculate_review_turnaround(prs).resample("W").median().reset_index()
    rt.columns = ["week", "review_hours"]
    fig = px.line(rt, x="week", y="review_hours", title="Review Turnaround (hours)", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

with q2:
    sizes = calculate_pr_size_distribution(prs)
    fig = px.histogram(sizes, nbins=30, title="PR Size Distribution (lines changed)", **PLOTLY_LAYOUT)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# ===== Section 3: Team Health ===============================================
st.header("👥 Team Health")
t1, t2 = st.columns(2)

with t1:
    bus = calculate_bus_factor(commits)
    fig = px.pie(
        names=list(bus.keys()),
        values=list(bus.values()),
        title="Commit Distribution (Bus Factor)",
        **PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

with t2:
    pr_authors = prs["author"].value_counts().reset_index()
    pr_authors.columns = ["author", "prs"]
    fig = px.bar(pr_authors, x="author", y="prs", title="PR Author Distribution", **PLOTLY_LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

# ===== Section 4: Sprint / Iteration View ==================================
st.header("📅 Sprint / Iteration View")
s1, s2 = st.columns(2)

with s1:
    fig = px.bar(
        sprints,
        x="sprint",
        y=["completed_items", "wip_items"],
        title="Throughput & WIP per Sprint",
        barmode="stack",
        **PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

with s2:
    lead = calculate_lead_time_per_sprint(prs, sprints)
    fig = px.line(
        lead,
        x="sprint",
        y="median_lead_time_hours",
        title="Lead Time per Sprint (median hours)",
        markers=True,
        **PLOTLY_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
st.divider()
st.caption("Built with Streamlit · Plotly · Pandas  |  [GitHub](https://github.com)")

# Engineering Dashboard

**A Streamlit dashboard for engineering team health and delivery metrics.**

> Built as a portfolio piece demonstrating how a Senior Product Manager thinks
> about engineering effectiveness — the metrics that matter, how to visualise
> them, and what levers they give a Chief Product Owner.

---

## 📸 Screenshot

<!-- Replace with an actual screenshot after first run -->

When you launch the dashboard you'll see:

| Area | What's shown |
|---|---|
| **Top KPI bar** | Median cycle time · PRs merged/week · Review coverage · After-hours ratio |
| **Delivery Velocity** | Weekly PR throughput bar chart, cycle-time trend line, monthly release frequency |
| **Code Quality** | Review turnaround trend, PR size histogram |
| **Team Health** | Bus-factor pie chart (commit distribution), PR author bar chart |
| **Sprint View** | Throughput + WIP stacked bars, lead-time-per-sprint trend |

All charts use **Plotly** with a dark-theme-compatible colour palette.

---

## ✨ Features

- **Demo mode** — works out of the box with realistic synthetic data (6 months, 8 team members, weekday/holiday patterns).
- **GitHub API mode** — point at any public (or private with token) repo and pull live PR + commit data.
- **Four metric sections** — Delivery Velocity, Code Quality, Team Health, Sprint View.
- **Clean architecture** — data fetching, metric calculation, and visualisation are fully separated.
- **Type-hinted, testable** — every metric function takes a DataFrame and returns a DataFrame/Series.

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/<you>/engineering-dashboard.git
cd engineering-dashboard

# Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run (demo data, no API key needed)
streamlit run app.py
```

The dashboard opens at `http://localhost:8501`.

### Using live GitHub data

```bash
cp .env.example .env
# Edit .env and paste a GitHub personal-access token
```

Then switch the sidebar toggle to **GitHub API** and enter an `owner/repo`.

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `GITHUB_TOKEN` | *(none)* | GitHub PAT for API mode |
| Sidebar → History | 6 months | How far back to load data |
| Sidebar → Data source | Demo data | Toggle between synthetic and live data |

---

## 📏 Metrics Explained

| Metric | What it measures | Why it matters |
|---|---|---|
| **Cycle time** | Hours from PR open → merge | Core DORA-adjacent flow metric |
| **Throughput** | PRs merged per week | Delivery cadence |
| **Review turnaround** | Hours from PR open → first review | Collaboration bottleneck signal |
| **PR size** | Lines added + deleted | Smaller PRs merge faster and have fewer defects |
| **Review coverage** | % of PRs with ≥ 1 review | Quality gate adherence |
| **Bus factor** | Commit distribution across authors | Knowledge-silo risk |
| **After-hours ratio** | % commits outside 09–18 / weekends | Sustainability signal |
| **Sprint throughput** | Items completed per sprint | Predictability |
| **WIP** | Items in progress | Little's Law — high WIP → long lead times |
| **Lead time** | Median cycle time per sprint | Sprint-over-sprint improvement trend |

---

## 🗂 Project Structure

```
engineering-dashboard/
├── app.py               # Streamlit UI
├── metrics.py           # Pure calculation functions
├── github_client.py     # GitHub REST API client (httpx)
├── data/
│   └── demo_data.py     # Synthetic data generator
├── requirements.txt
├── .env.example
└── LICENSE
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

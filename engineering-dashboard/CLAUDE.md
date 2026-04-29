# Engineering Dashboard — Dev Guide

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

No API key needed — demo mode loads synthetic data automatically.

To use real GitHub data: `cp .env.example .env` and add a `GITHUB_TOKEN`.

## Architecture

- `app.py` — Streamlit entry point, 4 dashboard sections (KPIs, delivery velocity, review health, team balance)
- `metrics.py` — 8 pure calculation functions (cycle time, velocity, bus factor, etc.), all type-hinted, take/return DataFrames
- `github_client.py` — httpx-based async GitHub API client
- `data/demo_data.py` — Realistic synthetic data generator (PRs, reviews, releases)

## Key Design Decisions

- Metric functions are pure (no side effects, no API calls) — easy to test
- Demo mode is the default so the dashboard is always runnable
- Charts use Plotly with dark-theme-compatible styling
- All metrics are ones a Staff PM / CPO would actually track

## Testing

```bash
python -c "from metrics import *; print('All imports OK')"
streamlit run app.py  # visual check in browser
```

No automated test suite yet.

## TODO

- [ ] Add unit tests for metric functions
- [ ] Add date range filter
- [ ] Add CSV export for metrics
- [ ] Add team comparison view
- [ ] Add DORA metrics (deployment frequency, change failure rate)

# `analytics/` — Reporting for Power BI

**Purpose:** make project data available to Power BI without building another service.

| Subfolder | What lives there |
|---|---|
| `sql/` | Versioned SQL files: views and read-only queries (daily summaries, alert counts, per-resident trends) |
| `exports/` | Generated CSV/Parquet files that Power BI Desktop imports (git-ignored) |

**Planned flow (milestone M7):** PostgreSQL → SQL views in `sql/` → export script →
CSV/Parquet in `exports/` → Power BI Desktop.

**Status:** empty — no SQL views or exports exist yet. See
[`../docs/roadmap.md`](../docs/roadmap.md) milestone M7.

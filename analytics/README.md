# `analytics/` — Reporting for Power BI

**Purpose:** make project data available to Power BI without building another service.

| Subfolder / file | What lives there |
|---|---|
| `sql/01_analytics_views.sql` | PostgreSQL views: check-ins, alerts, caregiver acknowledgement times, care-plan adherence, activity summaries, model runs, resident rollup |
| `sql/02_kpi_definitions.sql` | The KPI catalogue (numerator / denominator / missing-data handling) as a queryable view |
| `export_analytics.py` | Export script: SQL validation, KPI-catalogue check, and CSV export |
| `exports/` | Generated CSV files Power BI Desktop imports (git-ignored) |

---

## Status: **verified vs. not verified** (be precise)

| Thing | Status |
|---|---|
| Analytics SQL parses as valid PostgreSQL | ✅ **verified** (sqlglot, in the test suite) |
| Every `table.column` in the views exists in the real schema | ✅ **verified** (`--check-columns` against a migrated database; also in the test suite, with a negative control) |
| KPI definitions in SQL match the KPI code | ✅ **verified** (`--check-kpis`, in the test suite) |
| KPI calculations produce correct numbers | ✅ **verified** (24 unit tests + API tests against real stored rows) |
| Export script writes one CSV per view | ⚠️ **code complete, not yet executed against PostgreSQL** — see below |
| Views execute and return correct rows on PostgreSQL | ❌ **not yet verified** — no PostgreSQL server has been available |

**Why the last two rows matter.** Everything that can be checked *without* a
PostgreSQL server is checked automatically — including, since the column check
was added, whether each view references columns that actually exist. What still
cannot be checked offline is whether PostgreSQL executes these views and returns
the expected rows. **No CSV in `exports/` has been generated from a real
database yet**, and no Power BI report file exists.

> **Note on the roadmap (M7).** The roadmap's "done when" is *"Power BI Desktop
> imports an exported file and renders real data."* That has **not** happened.
> No `.pbix` exists in this repository and none is claimed. See
> [`../docs/powerbi-guide.md`](../docs/powerbi-guide.md) for the procedure to do it.

---

## Running it

From the repository root, using the project virtual environment:

```powershell
# 1. Validate the SQL and the KPI catalogue. Needs no database.
.\.venv\Scripts\python.exe analytics\export_analytics.py --dry-run

# 2. Check the SQL KPI view still matches the Python KPI catalogue.
.\.venv\Scripts\python.exe analytics\export_analytics.py --check-kpis

# 3. Check every table.column the views use exists in a migrated database.
#    Point this at the SQLite file you migrated, or your PostgreSQL URL.
$env:DATABASE_URL = "sqlite+pysqlite:///./backend/elderlife_local_dev.db"
.\.venv\Scripts\python.exe analytics\export_analytics.py --check-columns

# 4. Create the views in PostgreSQL.
psql -U elderlife_dev -d elderlife -f analytics\sql\01_analytics_views.sql
psql -U elderlife_dev -d elderlife -f analytics\sql\02_kpi_definitions.sql

# 5. Export every view to CSV in analytics\exports\.
.\.venv\Scripts\python.exe analytics\export_analytics.py
```

Step 5 needs a reachable PostgreSQL database with the views created. It reads
`DATABASE_URL` from `.env` via the application settings.

Steps 1–3 and 5 all work against the SQLite database documented in the root
[`README.md`](../README.md); only steps 4 and 5's PostgreSQL execution genuinely
require the PostgreSQL server.

---

## The KPI catalogue

Every KPI is defined by a **numerator**, a **denominator**, a **date range**,
and an explicit statement of **how missing data is handled**. The definitions
live in `backend/app/services/kpi_definitions.py` and are mirrored into
`sql/02_kpi_definitions.sql` so a Power BI page can display the definition
beside the number.

| KPI | Unit | Notebook |
|---|---|---|
| `alert_acknowledgement_rate` | ratio | share of alerts acknowledged |
| `alert_median_ack_seconds` | seconds | median time to acknowledge |
| `alert_resolution_rate` | ratio | share of alerts resolved |
| `high_priority_alert_count` | count | high/critical **operational priority** alerts |
| `checkin_completion_rate` | ratio | share of resolved check-ins taken |
| `medication_adherence_rate` | ratio | share of *logged* doses taken |
| `care_plan_adherence_rate` | ratio | share of actionable plan items adhered to |
| `model_metric_coverage` | ratio | share of finished model runs recording metrics |

### Two rules the KPIs enforce

1. **A missing denominator is not zero.** If a KPI has no data to stand on, it
   returns `is_measurable = false` with a reason, never `0.0` or `1.0`. Reporting
   0% when you simply have no data is a lie; reporting 100% is a worse one.
2. **Missing values are counted, not dropped.** Where rows are excluded (for
   example unacknowledged alerts from a median), the excluded count is reported
   alongside, so a good-looking number cannot hide a large, absent tail.

### What these KPIs do **not** say

- `high_priority_alert_count` counts **operational triage priority**. It is not a
  count of medically validated risks.
- `medication_adherence_rate` measures adherence **among logged doses**. A dose
  that was never logged at all is invisible to it. It cannot prove a missed dose.
- `model_metric_coverage` measures whether model runs *recorded* metrics. It says
  nothing about whether those metrics are good. Precision/recall/F1 come from the
  model evaluation pipeline, never from here.

---

## Power BI

There are two supported paths; both are documented step by step in
[`../docs/powerbi-guide.md`](../docs/powerbi-guide.md).

1. **CSV import** (simplest): import the files from `exports/`.
2. **Direct PostgreSQL connection**: point Power BI at the `analytics_*` views.

`exports/_manifest.json` records when each CSV was produced, from which database,
and its row count — so a report can never present stale data as current.

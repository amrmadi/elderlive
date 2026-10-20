# Connecting Power BI Desktop to ElderLife AI

**Audience:** someone who has never opened Power BI before.
**Status of this guide:** written, **not yet executed end-to-end.** No `.pbix`
report file exists in this repository. The steps below are the intended
procedure; the sections marked *verified* have been checked, the rest have not.

| Step | Verified? |
|---|---|
| Analytics SQL is valid PostgreSQL | ✅ verified by the test suite |
| Every column the views reference exists in the schema | ✅ verified by `--check-columns` against a migrated database |
| KPI definitions match between SQL and Python | ✅ verified by `--check-kpis` |
| Export script logic | ⚠️ code complete, not run against a live database |
| Views execute on PostgreSQL | ❌ not yet verified (no PostgreSQL has been available) |
| Power BI imports a CSV and renders | ❌ not yet done — no `.pbix` exists |

---

## What Power BI is, in one paragraph

Power BI Desktop is a free Windows application that reads data from a file or a
database, lets you build charts, and saves the result as a `.pbix` file. It does
not need the ElderLife backend to be running: it reads either the exported CSV
files or the PostgreSQL database directly.

---

## Before you start

1. **PostgreSQL must be running with data in it.** See the main
   [`README.md`](../README.md) for starting the database and seeding demo data.
2. **The analytics views must exist.** Create them once:

   ```powershell
   psql -U elderlife_dev -d elderlife -f analytics\sql\01_analytics_views.sql
   psql -U elderlife_dev -d elderlife -f analytics\sql\02_kpi_definitions.sql
   ```

3. **Generate the CSV exports** (optional; you can skip straight to the direct
   database connection in Option B):

   ```powershell
   .\.venv\Scripts\python.exe analytics\export_analytics.py
   ```

   This writes one CSV per view into `analytics\exports\`, plus
   `_manifest.json`. **Check the manifest**: it records when the files were
   generated and how many rows each has. A `row_count` of 0 means the view ran
   and found nothing — that is a real result, and it looks very different from a
   missing file.

---

## Option A — Import the CSV files (simplest)

1. Open **Power BI Desktop**.
2. **Home → Get data → Text/CSV**.
3. Choose `analytics\exports\analytics_alerts_daily.csv` and click **Open**.
4. Power BI shows a preview. Click **Transform Data** if you want to check column
   types, or **Load** to accept them.
5. Repeat **Get data → Text/CSV** for each other CSV you want:
   `analytics_checkin_daily`, `analytics_caregiver_acknowledgement`,
   `analytics_care_plan_adherence`, `analytics_activity_daily`,
   `analytics_model_runs`, `analytics_resident_rollup`,
   `analytics_kpi_definitions`.
6. Build visuals on the **Report** tab, then **File → Save As** to create a
   `.pbix`.

**Important:** this is a static import. If the underlying data changes, repeat
the export and click **Refresh** in Power BI. The `.pbix` does not poll the
database.

---

## Option B — Connect directly to PostgreSQL

This gives live data each time you refresh.

1. In Power BI Desktop: **Home → Get data → More… → Database → PostgreSQL
   database**.
2. **Server:** `localhost:5432`
3. **Database:** `elderlife`
4. Choose **Import** (simpler) or **DirectQuery** (live, slower).
5. Enter the credentials from your local `.env` file. These are **your own
   development credentials** — never commit real ones, and never point a
   published report at a production database with a personally-identifying view.
6. In the navigator, tick the `analytics_*` views and click **Load**.

---

## Suggested first report (one page)

| Visual | Source view | Fields |
|---|---|---|
| Card | `analytics_kpi_definitions` | the definition text, so the page explains itself |
| Line chart | `analytics_alerts_daily` | date on the axis, `high_priority_alert_count` as the value |
| Table | `analytics_caregiver_acknowledgement` | caregiver, `median_ack_seconds` |
| Bar chart | `analytics_activity_daily` | `activity_type` vs `total_duration_seconds` |
| Slicer | `analytics_alerts_daily` | `alert_date` — **always include a date slicer** |

---

## Four honesty rules for any report built on this data

These are not style preferences; they are the difference between a report that
informs and one that misleads.

1. **Always show the date range.** Every KPI is computed over a window. A number
   without its window cannot be interpreted.
2. **Separate simulated from real data.** Activity views expose
   `simulated_event_count` and `all_events_simulated`. Seeded demo data is
   labelled `simulated` throughout. Filter it out, or label the visual clearly.
3. **Show "not measurable" as "not measurable".** Where a KPI has no data, the
   API returns `is_measurable = false`. Do not map that to a zero in the chart.
4. **Never relabel operational priority as medical risk.** Alerts carry an
   operational triage priority. A high-priority alert means "someone should look
   at this soon", not "this resident is medically at risk". Validated risk lives
   in `risk_events` and is a separate thing.

---

## Privacy notes

- Never publish a report containing personal data to the public web.
- The analytics views contain resident **display names**. For distribution
  outside the care team, build a report against an anonymised extract instead.
- Public research datasets (UP-Fall, CASAS, UCI HAR, SisFall) live in `data/` and
  are **never** joined into these reporting views. They are training data, not
  application records.

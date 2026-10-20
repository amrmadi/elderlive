"""Export analytics data to CSV for Power BI, and verify the KPI catalogue.

Two modes
---------
1. **Export (default).** Connects to the configured database, reads the
   `analytics_*` views, and writes one CSV per view into `analytics/exports/`.
   A companion `_manifest.json` records exactly when each file was produced,
   from which database, and how many rows it contained — so a CSV can never be
   presented as fresher than it is.

2. **`--check-kpis`.** Verifies that the KPI definitions in
   `analytics/sql/02_kpi_definitions.sql` still match
   `backend/app/services/kpi_definitions.py`. Exits non-zero on drift, so the
   two cannot silently disagree.

**`--dry-run`** does everything except touch a database: it validates the SQL
and reports which views *would* be exported. This is what makes the script
testable without PostgreSQL.

Nothing here invents data. If a view returns zero rows, the CSV is still written
with its header and `row_count: 0` is recorded in the manifest, because "we
looked and found nothing" is a real, reportable result — unlike a missing file,
which is indistinguishable from "the export failed".
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Running this file directly (`python analytics/export_analytics.py`) puts
# `analytics/` on sys.path, not the repository root, so `import backend...`
# would fail. Adding the root explicitly makes the script work both as a direct
# command and as an imported module in tests.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SQL_DIR = REPO_ROOT / "analytics" / "sql"
EXPORT_DIR = REPO_ROOT / "analytics" / "exports"
VIEWS_SQL = SQL_DIR / "01_analytics_views.sql"
KPI_SQL = SQL_DIR / "02_kpi_definitions.sql"

# Views exported to CSV, in dependency-free order.
EXPORT_VIEWS = (
    "analytics_kpi_definitions",
    "analytics_checkin_daily",
    "analytics_alerts_daily",
    "analytics_caregiver_acknowledgement",
    "analytics_care_plan_adherence",
    "analytics_activity_daily",
    "analytics_model_runs",
    "analytics_resident_rollup",
)


def validate_sql() -> list[str]:
    """Parse the analytics SQL as PostgreSQL; raise on a syntax error.

    Returns the names of the views defined in `01_analytics_views.sql`.
    """
    try:
        import sqlglot
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise SystemExit(
            "sqlglot is required to validate the analytics SQL. "
            "Install it with: .venv\\Scripts\\python.exe -m pip install sqlglot"
        ) from exc

    # A deliberately-broken statement must be rejected, otherwise a successful
    # parse below would prove nothing about the parser's strictness.
    try:
        sqlglot.parse("CREATE VIEW v AS SELECT FROM WHERE (;", dialect="postgres")
    except Exception:
        pass
    else:  # pragma: no cover - only if sqlglot behaviour changes
        raise SystemExit(
            "SQL self-check failed: the parser accepted invalid SQL, so its "
            "verdict on our files cannot be trusted."
        )

    for path in (VIEWS_SQL, KPI_SQL):
        try:
            sqlglot.parse(path.read_text(encoding="utf-8"), dialect="postgres")
        except Exception as exc:
            raise SystemExit(f"{path.name} is not valid PostgreSQL: {exc}") from exc

    # Views are declared across both SQL files, so collect from both.
    names: list[str] = []
    for path in (VIEWS_SQL, KPI_SQL):
        for statement in sqlglot.parse(path.read_text(encoding="utf-8"), dialect="postgres"):
            if statement is None or statement.key != "create":
                continue
            target = statement.this
            name = getattr(target, "name", None)
            if isinstance(name, str) and name.startswith("analytics_"):
                names.append(name)
    return names


# Table names that are *other views* defined in these same files. A reference to
# one of these is expected and must not be looked up as a base table.
_DERIVED_VIEWS = {
    "analytics_checkin_daily",
    "analytics_alerts_daily",
    "analytics_caregiver_acknowledgement",
    "analytics_care_plan_adherence",
    "analytics_activity_daily",
    "analytics_model_runs",
    "analytics_resident_rollup",
}


def check_columns(database_url: str | None = None) -> int:
    """Verify every `table.column` the views use exists in the real schema.

    Syntax parsing proves the SQL is *shaped* correctly; it says nothing about
    whether `a.severity` is a real column. This walks each view's expression
    tree, collects qualified column references, and compares them against the
    columns the migration actually created in a database.

    `database_url` defaults to `DATABASE_URL` from the environment, then to the
    application's configured database. A database whose schema is up to date is
    required — run `alembic upgrade head` first.
    """
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise SystemExit(
            "sqlglot is required. Install it with: "
            ".venv\\Scripts\\python.exe -m pip install sqlglot"
        ) from exc

    schema = _read_schema_columns(database_url)

    if not schema:
        raise SystemExit(
            "Could not read any tables from the database — the column check would "
            "pass vacuously, so it is being treated as a failure. Run "
            "`alembic upgrade head` first."
        )

    problems: list[str] = []
    checked = 0

    for path in (VIEWS_SQL, KPI_SQL):
        for statement in sqlglot.parse(path.read_text(encoding="utf-8"), dialect="postgres"):
            if statement is None or statement.key != "create":
                continue
            view_name = getattr(statement.this, "name", "?")
            if not (isinstance(view_name, str) and view_name.startswith("analytics_")):
                continue

            for column in statement.find_all(exp.Column):
                table = column.table
                if not table:
                    # Unqualified: cannot attribute it to one table without full
                    # scope resolution, which sqlglot does not do for us here.
                    continue
                if table in _DERIVED_VIEWS:
                    continue
                real_table = _resolve_alias(table, statement)
                if real_table is None:
                    continue
                if real_table not in schema:
                    problems.append(
                        f"{view_name}: unknown table `{real_table}` (as `{table}`)"
                    )
                    continue
                checked += 1
                if column.name not in schema[real_table]:
                    problems.append(
                        f"{view_name}: `{real_table}.{column.name}` — no such column"
                    )

    if problems:
        print("Column check FAILED:")
        for problem in problems:
            print("  -", problem)
        return 1

    print(
        f"Column check passed: {checked} qualified column references across "
        f"{len(schema)} tables all exist."
    )
    return 0


def _resolve_alias(reference: str, statement) -> str | None:
    """Map an alias (or bare table name) used in a view back to a real table.

    Returns None when the name is neither a table nor a known alias, so the
    caller can decide whether that is a problem.
    """
    from sqlglot import exp

    # `FROM residents r` / `JOIN alerts AS a` — build alias -> table.
    alias_to_table: dict[str, str] = {}
    for table_expr in statement.find_all(exp.Table):
        table_name = table_expr.name
        alias = table_expr.alias
        if alias:
            alias_to_table[alias] = table_name
    if reference in alias_to_table:
        return alias_to_table[reference]
    return reference


def _read_schema_columns(database_url: str | None = None) -> dict[str, set[str]]:
    """Read table -> column names from a migrated database.

    The database is the source of truth: these are the columns the migration
    actually creates, not a hand-written list that could drift. Uses SQLAlchemy's
    inspector, so the same check runs against SQLite locally and PostgreSQL in
    CI without changing a line.
    """
    try:
        from sqlalchemy import create_engine, inspect
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise SystemExit(f"SQLAlchemy is required for --check-columns: {exc}") from exc

    url = database_url or os.environ.get("DATABASE_URL")
    if not url:
        sys.path.insert(0, str(REPO_ROOT))
        from backend.app.core.config import get_settings  # noqa: PLC0415

        url = get_settings().database_url

    engine = create_engine(url)
    try:
        inspector = inspect(engine)
        return {
            table: {col["name"] for col in inspector.get_columns(table)}
            for table in inspector.get_table_names()
        }
    finally:
        engine.dispose()


def check_kpis() -> int:
    """Verify SQL KPI descriptions match the Python catalogue. 0 = in sync."""
    import re

    from backend.app.services.kpi_definitions import ALL_KPIS

    sql_text = KPI_SQL.read_text(encoding="utf-8")

    # The VALUES rows are ordered tuples; pull the first field of each row.
    keys_in_sql = re.findall(r"^\s*\(\s*\n\s*'([a-z_]+)',", sql_text, flags=re.MULTILINE)
    keys_in_code = [d.key for d in ALL_KPIS]

    problems: list[str] = []

    missing_from_sql = [k for k in keys_in_code if k not in keys_in_sql]
    extra_in_sql = [k for k in keys_in_sql if k not in keys_in_code]
    if missing_from_sql:
        problems.append(f"In code but not in SQL view: {missing_from_sql}")
    if extra_in_sql:
        problems.append(f"In SQL view but not in code: {extra_in_sql}")

    # Compare numerator/denominator text. Two normalisations are applied, both
    # reversible and purely cosmetic:
    #   * typographic punctuation -> ASCII (curly quotes, en/em dashes);
    #   * SQL's doubled single quotes ('') -> one quote (a literal must escape
    #     its quote character inside a SQL string).
    # Word-level differences still fail, which is the drift we actually care
    # about.
    def normalise(text: str) -> str:
        squashed = " ".join(text.split())
        for source, target in (
            ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
            ("\u2014", "-"), ("\u2013", "-"), ("\u2026", "..."),
        ):
            squashed = squashed.replace(source, target)
        # SQL string-literal escaping: '' means one literal quote.
        squashed = squashed.replace("''", "'")
        return squashed

    normalised_sql = normalise(sql_text)
    for definition in ALL_KPIS:
        for label, text in (
            ("numerator", definition.numerator_description),
            ("denominator", definition.denominator_description),
            ("missing-data handling", definition.missing_data_handling),
        ):
            if normalise(text) not in normalised_sql:
                problems.append(
                    f"{definition.key}: {label} text in code does not appear in "
                    "02_kpi_definitions.sql"
                )

    if problems:
        print("KPI catalogue DRIFT detected:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"KPI catalogue in sync: {len(keys_in_code)} definitions match the SQL view.")
    return 0


def _connect():
    """Open a database connection from the application settings."""
    from sqlalchemy import create_engine

    from backend.app.core.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url)
    return engine


def export(dry_run: bool = False) -> int:
    """Write one CSV per analytics view plus a manifest."""
    views = validate_sql()
    print(f"SQL validated as PostgreSQL. Views found: {len(views)}")
    for view in views:
        print(f"  - {view}")

    unknown = [v for v in EXPORT_VIEWS if v not in views]
    if unknown:
        raise SystemExit(
            f"These views are listed for export but not defined in SQL: {unknown}"
        )

    if dry_run:
        print("\n--dry-run: no database was contacted and no files were written.")
        return 0

    from sqlalchemy import text

    engine = _connect()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc)

    manifest: dict[str, object] = {
        "generated_at": generated_at.isoformat(),
        "database_url_scheme": engine.url.drivername,
        "database_name": engine.url.database,
        "source": "analytics/sql/01_analytics_views.sql",
        "files": [],
    }

    with engine.connect() as connection:
        for view in EXPORT_VIEWS:
            result = connection.execute(text(f"SELECT * FROM {view}"))
            columns = list(result.keys())
            rows = result.fetchall()

            target = EXPORT_DIR / f"{view}.csv"
            with target.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(["" if v is None else v for v in row])

            manifest["files"].append(  # type: ignore[union-attr]
                {
                    "view": view,
                    "file": target.name,
                    "row_count": len(rows),
                    "column_count": len(columns),
                }
            )
            print(f"wrote {target.name}: {len(rows)} row(s)")

    manifest_path = EXPORT_DIR / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {manifest_path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate SQL and list views without connecting to a database.",
    )
    parser.add_argument(
        "--check-kpis",
        action="store_true",
        help="Verify the SQL KPI view matches the Python KPI catalogue, then exit.",
    )
    parser.add_argument(
        "--check-columns",
        action="store_true",
        help=(
            "Verify every table.column the views reference exists in the real "
            "schema, then exit. Needs a migrated database."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "Database to check with --check-columns. Defaults to DATABASE_URL, "
            "then to the application's configured database."
        ),
    )
    args = parser.parse_args(argv)

    if args.check_kpis:
        return check_kpis()
    if args.check_columns:
        return check_columns(args.database_url)
    return export(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())

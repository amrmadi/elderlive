"""Tests for the analytics layer: SQL view validity and KPI-catalogue sync.

These run without PostgreSQL. They check the things that *can* be checked
offline and that are most likely to break silently:

* the analytics SQL is syntactically valid PostgreSQL;
* the KPI definitions in SQL match the KPI definitions in Python;
* the export script refuses to invent a database when none is available.

What these tests deliberately do NOT claim: that the views return correct rows
against a real PostgreSQL server. That requires a live database and is verified
separately; see `analytics/README.md`.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYTICS = REPO_ROOT / "analytics"
EXPORT_SCRIPT = ANALYTICS / "export_analytics.py"
VIEWS_SQL = ANALYTICS / "sql" / "01_analytics_views.sql"
KPI_SQL = ANALYTICS / "sql" / "02_kpi_definitions.sql"

pytest.importorskip("sqlglot", reason="sqlglot is needed to validate the analytics SQL")

import sqlglot  # noqa: E402  (import after the skip guard, intentionally)


def _parse(path: Path):
    return sqlglot.parse(path.read_text(encoding="utf-8"), dialect="postgres")


# ---------------------------------------------------------------------------
# SQL validity
# ---------------------------------------------------------------------------


def test_sqlglot_actually_rejects_invalid_sql() -> None:
    """Guard: if the parser were permissive, our 'valid' verdicts would be worthless."""
    with pytest.raises(Exception):
        sqlglot.parse("CREATE VIEW v AS SELECT FROM WHERE (;", dialect="postgres")


def test_views_sql_is_valid_postgresql() -> None:
    statements = [s for s in _parse(VIEWS_SQL) if s is not None]
    assert statements, "01_analytics_views.sql contained no statements"


def test_kpi_sql_is_valid_postgresql() -> None:
    statements = [s for s in _parse(KPI_SQL) if s is not None]
    assert statements, "02_kpi_definitions.sql contained no statements"


def _view_names(path: Path) -> set[str]:
    names: set[str] = set()
    for statement in _parse(path):
        if statement is None or statement.key != "create":
            continue
        name = getattr(statement.this, "name", None)
        if isinstance(name, str) and name.startswith("analytics_"):
            names.add(name)
    return names


def test_all_expected_views_are_defined() -> None:
    available = _view_names(VIEWS_SQL) | _view_names(KPI_SQL)
    expected = {
        "analytics_checkin_daily",
        "analytics_alerts_daily",
        "analytics_caregiver_acknowledgement",
        "analytics_care_plan_adherence",
        "analytics_activity_daily",
        "analytics_model_runs",
        "analytics_resident_rollup",
        "analytics_kpi_definitions",
    }
    assert expected <= available, f"Missing views: {sorted(expected - available)}"


def test_views_do_not_contain_write_statements() -> None:
    """Analytics views must be read-only projections.

    `create` (the views), `drop` (the idempotent drop-if-exists), and `comment`
    (documentation attached to a view) are the only statements allowed. Anything
    that writes rows — INSERT/UPDATE/DELETE/ALTER — would mean this layer is not
    read-only.
    """
    allowed = {"create", "drop", "comment"}
    for path in (VIEWS_SQL, KPI_SQL):
        for statement in _parse(path):
            if statement is None:
                continue
            assert statement.key in allowed, (
                f"{path.name} contains a non-read-only statement: {statement.key}"
            )


# ---------------------------------------------------------------------------
# KPI catalogue sync (the drift guard)
# ---------------------------------------------------------------------------


def test_kpi_catalogue_in_sync_with_sql_view() -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--check-kpis"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--check-kpis reported drift:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )
    assert "in sync" in result.stdout


def test_kpi_drift_check_detects_real_drift(tmp_path: Path, monkeypatch) -> None:
    """Negative control: the checker must fail when the SQL is edited out of sync.

    Without this test, a checker that always passed would look identical to a
    checker that worked.
    """
    sys.path.insert(0, str(REPO_ROOT))
    import analytics.export_analytics as module

    monkeypatch.setattr(module, "KPI_SQL", tmp_path / "02_kpi_definitions.sql")
    module.KPI_SQL.write_text(
        "CREATE VIEW analytics_kpi_definitions AS SELECT * FROM (VALUES ('wrong_key','n','ratio','x','y','z','')) AS t(kpi_key,kpi_name,unit,numerator_description,denominator_description,missing_data_handling,notes);",
        encoding="utf-8",
    )

    assert module.check_kpis() == 1


# ---------------------------------------------------------------------------
# Export script behaviour without a database
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing_and_exits_cleanly(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "no database was contacted" in result.stdout


def test_dry_run_lists_every_export_view() -> None:
    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    for view in (
        "analytics_checkin_daily",
        "analytics_alerts_daily",
        "analytics_caregiver_acknowledgement",
        "analytics_care_plan_adherence",
        "analytics_activity_daily",
        "analytics_model_runs",
        "analytics_resident_rollup",
        "analytics_kpi_definitions",
    ):
        assert view in result.stdout


def test_export_module_does_not_touch_a_database_until_asked() -> None:
    """`validate_sql` must be pure: it validates text and returns names only."""
    sys.path.insert(0, str(REPO_ROOT))
    import analytics.export_analytics as module

    names = module.validate_sql()
    assert "analytics_alerts_daily" in names


# ---------------------------------------------------------------------------
# Column references vs the real schema
# ---------------------------------------------------------------------------


@pytest.fixture()
def migrated_sqlite(tmp_path: Path) -> str:
    """A fresh SQLite database with the real migrations applied.

    `--check-columns` needs an actual schema to compare against. Migrating a
    throwaway SQLite file is the closest thing to PostgreSQL that runs without a
    server, and it exercises the same migration the real database uses.
    """
    db_path = tmp_path / "column_check.db"
    url = f"sqlite+pysqlite:///{db_path}"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(REPO_ROOT / "backend" / "alembic.ini"),
            "upgrade",
            "head",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT / "backend"),
        env={**os.environ, "DATABASE_URL": url},
    )
    assert result.returncode == 0, (
        f"alembic upgrade failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )
    return url


def test_check_columns_passes_against_the_real_schema(migrated_sqlite: str) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(EXPORT_SCRIPT),
            "--check-columns",
            "--database-url",
            migrated_sqlite,
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--check-columns failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
    )
    assert "Column check passed" in result.stdout


def test_check_columns_detects_a_bogus_column(
    migrated_sqlite: str, tmp_path: Path, monkeypatch
) -> None:
    """Negative control: the checker must fail when a view names a column that
    does not exist, otherwise a passing check proves nothing."""
    sys.path.insert(0, str(REPO_ROOT))
    import analytics.export_analytics as module

    broken = tmp_path / "01_analytics_views.sql"
    original = module.VIEWS_SQL.read_text(encoding="utf-8")
    # A plausible-looking typo: the kind a human would actually make.
    broken.write_text(original.replace("a.severity", "a.severity_typo"), encoding="utf-8")

    # The KPI view is checked too, so give it a real (empty) file rather than a
    # missing path, or the check would fail for the wrong reason.
    empty_kpi = tmp_path / "02_kpi_definitions.sql"
    empty_kpi.write_text("", encoding="utf-8")

    monkeypatch.setattr(module, "VIEWS_SQL", broken)
    monkeypatch.setattr(module, "KPI_SQL", empty_kpi)

    assert module.check_columns(migrated_sqlite) == 1


def test_check_columns_refuses_to_pass_vacuously(tmp_path: Path) -> None:
    """An empty schema must be an error, not a silent pass."""
    sys.path.insert(0, str(REPO_ROOT))
    import analytics.export_analytics as module

    empty_db = tmp_path / "empty.db"
    url = f"sqlite+pysqlite:///{empty_db}"

    with pytest.raises(SystemExit):
        module.check_columns(url)

"""Check that the analytics SQL references tables and columns that really exist.

The analytics views and KPI queries have never been executed, because doing so
needs PostgreSQL and Docker is not installed on this machine. This script
verifies the next best thing offline: that every table and column the SQL names
is present in the SQLAlchemy models. A typo in a view would otherwise only
surface on the day someone finally runs it.

It uses `sqlglot` to parse the SQL properly rather than guessing with regex,
and it exits non-zero on any unknown reference so a failure is unambiguous.

Run from the repository root:
    .venv\\Scripts\\python.exe tools\\validate_analytics_sql.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Make the repository root importable so `backend.app.models` resolves no matter
# which directory the script is run from.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import sqlglot
    from sqlglot import exp
except ImportError:  # pragma: no cover - environment problem, reported clearly
    print("sqlglot is not installed; cannot parse the SQL. Install it with:")
    print("    .venv\\Scripts\\python.exe -m pip install sqlglot")
    sys.exit(2)

# The models must be importable to know what the schema contains.
import backend.app.models  # noqa: F401,E402  (registers every table)
from backend.app.db.base import Base  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- What the ORM says exists ------------------------------------------------
known_tables: dict[str, set[str]] = {
    table.name: {col.name for col in table.columns}
    for table in Base.metadata.tables.values()
}

# Views this SQL defines itself are valid relation names in later statements.
defined_views: set[str] = set()
for _path in sorted((ROOT / "analytics" / "sql").glob("*.sql")):
    for _m in re.finditer(
        r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:VIEW|MATERIALIZED\s+VIEW)\s+([A-Za-z_][A-Za-z0-9_]*)",
        _path.read_text(encoding="utf-8"),
        re.IGNORECASE,
    ):
        defined_views.add(_m.group(1))
        known_tables.setdefault(_m.group(1), set())  # columns unknown; skip column checks

# Common SQL aliases that are not table columns and must not be flagged.
NOT_A_COLUMN = {"*", ""}

errors: list[str] = []
checked_tables: set[str] = set()
view_tables: set[str] = set()
checked_columns = 0


def tables_in(node: exp.Expression) -> dict[str, set[str]]:
    """Map each alias (or table name) used in a FROM/JOIN to its real table name."""
    mapping: dict[str, set[str]] = {}
    for table in node.find_all(exp.Table):
        real = table.name
        alias = table.alias or real
        if real in known_tables:
            mapping[alias] = known_tables[real]
            mapping[alias.lower()] = known_tables[real]
            if real in defined_views:
                view_tables.add(real)
            else:
                checked_tables.add(real)
        else:
            errors.append(f"unknown table referenced: {real!r}")
    return mapping


def check_statements(sql: str, source: str) -> None:
    global checked_columns
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:  # noqa: BLE001 - report any parse failure verbatim
        errors.append(f"{source}: failed to parse: {exc}")
        return

    for statement in statements:
        if statement is None:
            continue
        scope: dict[str, set[str]] = {}
        # CTE names are legitimate relation names inside the statement.
        for cte in statement.find_all(exp.CTE):
            name = cte.alias_or_name
            if name:
                scope[name] = set()
        scope.update(tables_in(statement))

        for column in statement.find_all(exp.Column):
            name = column.name
            if name in NOT_A_COLUMN:
                continue
            table = column.table
            if table:
                cols = scope.get(table) or scope.get(table.lower())
                if cols is None:
                    # The qualifier is a CTE or an alias we could not resolve;
                    # report rather than ignore, so nothing slips through.
                    errors.append(f"{source}: column {table}.{name} uses an unresolved table")
                    continue
                if cols and name not in cols:
                    errors.append(f"{source}: {table}.{name} is not a column of that table")
                else:
                    checked_columns += 1
            else:
                # Unqualified: it must appear in at least one table in scope.
                if scope and not any(name in cols for cols in scope.values() if cols):
                    errors.append(f"{source}: unqualified column {name!r} not found in any table in scope")
                else:
                    checked_columns += 1


sql_files = sorted((ROOT / "analytics" / "sql").glob("*.sql"))
if not sql_files:
    print("No SQL files found under analytics/sql — nothing to check.")
    sys.exit(1)

for path in sql_files:
    check_statements(path.read_text(encoding="utf-8"), path.name)
    print(f"parsed: {path.name}")

print()
print(f"tables confirmed to exist : {len(checked_tables)} -> {sorted(checked_tables)}")
print(f"views defined by this SQL : {len(view_tables)} -> {sorted(view_tables)}")
print(f"column references checked : {checked_columns}")

if errors:
    print()
    print("ANALYTICS SQL REFERENCE CHECK: FAIL")
    # De-duplicate and show a bounded number so the output stays readable.
    seen = []
    for e in errors:
        if e not in seen:
            seen.append(e)
    for e in seen[:40]:
        print("  *", e)
    if len(seen) > 40:
        print(f"  ... and {len(seen) - 40} more")
    sys.exit(1)

print()
print("ANALYTICS SQL REFERENCE CHECK: PASS")
print("NOTE: this confirms the SQL *names real tables and columns*. It does NOT")
print("      prove the queries run or return correct numbers - that needs")
print("      PostgreSQL, which is not available on this machine.")

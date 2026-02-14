"""
Database repair script.

Checks for missing tables/columns/indexes based on SQLAlchemy models,
and optionally applies safe fixes (create table / add column / add index).

Usage:
  python repair_db.py            # dry-run (print plan)
  python repair_db.py --apply    # apply changes
"""
import argparse
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateTable

from config import get_db_url
from models import Base


def render_column_ddl(col, dialect):
    col_type = col.type.compile(dialect=dialect)

    # If column is NOT NULL but has no server default, adding it may fail on existing rows.
    # For safety, allow NULL and warn.
    nullable = col.nullable
    if not nullable and col.default is None and col.server_default is None:
        nullable = True
        warn = True
    else:
        warn = False

    null_sql = "NULL" if nullable else "NOT NULL"
    return f"{col_type} {null_sql}", warn


def main():
    parser = argparse.ArgumentParser(description="Repair database schema")
    parser.add_argument("--apply", action="store_true", help="Apply changes to the database")
    parser.add_argument("--verbose", action="store_true", help="Print verbose details")
    args = parser.parse_args()

    engine = create_engine(get_db_url())
    inspector = inspect(engine)

    existing_tables = set(inspector.get_table_names())

    plans = []
    warnings = []

    # 1) Missing tables
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            plans.append(("create_table", table.name, None))
            continue

        # 2) Missing columns
        existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
        for col in table.columns:
            if col.name in existing_columns:
                continue
            col_ddl, warned = render_column_ddl(col, engine.dialect)
            if warned:
                warnings.append(
                    f"Column {table.name}.{col.name} is NOT NULL in models but will be added as NULL."
                )
            plans.append(("add_column", table.name, (col.name, col_ddl)))

        # 3) Missing indexes (by name)
        existing_indexes = {idx["name"] for idx in inspector.get_indexes(table.name)}
        for idx in table.indexes:
            if idx.name in existing_indexes:
                continue
            plans.append(("add_index", table.name, idx))

    if not plans:
        print("Schema looks complete. No changes needed.")
        return 0

    print("Planned changes:")
    for action, table_name, payload in plans:
        if action == "create_table":
            print(f"- Create table: {table_name}")
        elif action == "add_column":
            col_name, col_ddl = payload
            print(f"- Add column: {table_name}.{col_name} ({col_ddl})")
        elif action == "add_index":
            print(f"- Add index: {table_name}.{payload.name}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"- {w}")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to make changes.")
        return 0

    # Apply changes
    with engine.begin() as conn:
        for action, table_name, payload in plans:
            if action == "create_table":
                table = Base.metadata.tables[table_name]
                if args.verbose:
                    print(f"Creating table {table_name}...")
                conn.execute(CreateTable(table).compile(engine))
            elif action == "add_column":
                col_name, col_ddl = payload
                if args.verbose:
                    print(f"Adding column {table_name}.{col_name}...")
                sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{col_name}` {col_ddl}"
                conn.execute(text(sql))
            elif action == "add_index":
                idx = payload
                if args.verbose:
                    print(f"Creating index {idx.name} on {table_name}...")
                idx.create(bind=conn)

    print("Schema repair completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

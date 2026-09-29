#!/usr/bin/env python3

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app

from sqlalchemy import inspect, text
from database.db import DATABASE_URL, engine, init_db


def main():
    parser = argparse.ArgumentParser(description="Wipe or reset PPIP database tables")
    parser.add_argument(
        "--yes", action="store_true", help="actually delete; omit for a dry run"
    )
    parser.add_argument(
        "--reset-schema",
        action="store_true",
        help="drop and recreate all tables according to SQLModel models",
    )
    args = parser.parse_args()

    print(f"database: {DATABASE_URL}")

    inspector = inspect(engine)
    try:
        tables = [
            t
            for t in inspector.get_table_names()
            if not t.startswith("sqlite_") and not t.startswith("pg_")
        ]
    except Exception as e:
        sys.exit(f"failed to inspect database tables: {e}")

    if not tables and not args.reset_schema:
        sys.exit("no tables found — is DATABASE_URL pointing where you think?")

    with engine.connect() as connection:
        for table in tables:
            count = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            print(f"  {table}: {count} rows")

        if args.reset_schema:
            if not args.yes:
                print("\ndry run — specify --yes with --reset-schema to drop and recreate tables.")
                return

            print("\nDropping and recreating all tables...")
            for table in tables:
                if engine.dialect.name == "postgresql":
                    connection.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                else:
                    connection.execute(text(f'DROP TABLE IF EXISTS "{table}"'))
            connection.commit()
            init_db()
            print("Database schema successfully recreated!")
            return

        if not args.yes:
            print("\ndry run — nothing deleted. Re-run with --yes to wipe.")
            return

        print("\nWiping tables...")
        if engine.dialect.name == "postgresql":
            for table in tables:
                connection.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
            connection.commit()
        else:
            for table in tables:
                connection.execute(text(f'DELETE FROM "{table}"'))
            if connection.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE name='sqlite_sequence'")
            ).scalar():
                connection.execute(text("DELETE FROM sqlite_sequence"))
            connection.commit()
            connection.execute(text("VACUUM"))

        print("\nwiped:")
        for table in tables:
            count = connection.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            print(f"  {table}: {count} rows")


if __name__ == "__main__":
    main()

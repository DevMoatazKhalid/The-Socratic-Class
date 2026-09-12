"""
Database migration runner.

Executes all SQL migration scripts in database/migrations/ sequentially.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.is_file():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


def run_migrations(database_url: str | None = None) -> bool:
    db_url = database_url or os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL is not set.")
        return False

    migrations_dir = _PROJECT_ROOT / "database" / "migrations"
    if not migrations_dir.is_dir():
        print(f"ERROR: Migrations directory not found at {migrations_dir}")
        return False

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print("No SQL migration files found.")
        return True

    print(f"Connecting to database...")
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Ensure migration tracker table exists
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS _schema_migrations (
                        filename VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    """
                )
                cur.execute("SELECT filename FROM _schema_migrations;")
                applied = {row[0] for row in cur.fetchall()}

                for sql_file in sql_files:
                    if sql_file.name in applied:
                        print(f"  [SKIP] {sql_file.name} (already applied)")
                        continue

                    print(f"  [APPLY] {sql_file.name}...")
                    sql_content = sql_file.read_text(encoding="utf-8")
                    cur.execute(sql_content)
                    cur.execute(
                        "INSERT INTO _schema_migrations (filename) VALUES (%s);",
                        (sql_file.name,),
                    )
                    print(f"  [SUCCESS] {sql_file.name}")

        print("All migrations completed successfully.")
        return True
    except Exception as exc:
        print(f"Migration failed: {exc}")
        return False


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_migrations(url)
    sys.exit(0 if success else 1)

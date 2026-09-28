"""Apply only citation v2's additive schema, atomically. Existing answers are retained.

Run from apps/api: .venv/Scripts/python scripts/migrate_citations.py
DATABASE_URL may use the project's existing IPv4 session pooler.
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import db


def main():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    sql = Path(db.SCHEMA).read_text(encoding="utf-8")
    block = sql.split("-- Citation v2:", 1)[1]
    block = block[block.index("alter table"):].split("alter table public.notifications", 1)[0]
    try:
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=15) as conn:
            for statement in db.statements(block):
                conn.execute(statement)
            conn.execute("notify pgrst, 'reload schema'")
    except Exception as error:  # noqa: BLE001 - any failure: the message may hold the connection string, so it is never printed
        print(f"Citation migration failed ({type(error).__name__}). Check DATABASE_URL connectivity and permissions.")
        return 1
    print("Citation v2 schema applied. Existing answers retained; PostgREST schema reload requested.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

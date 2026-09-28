"""Versioned migrations (SD-5.1): apps/api/migrations/NNNN_name.sql, each applied once, in order, in one transaction.

    .venv/Scripts/python -m app.migrate            # apply every pending migration (also: python -m app.db)
    .venv/Scripts/python -m app.migrate status     # applied and pending versions
    .venv/Scripts/python -m app.migrate down       # undo the latest one, when it has NNNN_name.down.sql

`schema_migrations` records each version with the checksum of its file. A migration that changed after it was applied
is refused: write the next numbered file instead. A failing migration rolls back whole and records nothing. Each file
goes to the server as one query, so a slow or flaky connection (the pooler from the founder's network) costs one
round trip per migration, not one per statement.
"""

import hashlib
import os
import re
import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent.parent / "migrations"
FILE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")

TABLE = """
create table if not exists public.schema_migrations (
  version text primary key,
  name text not null,
  checksum text not null,
  applied_at timestamptz not null default now()
);
alter table public.schema_migrations enable row level security;
revoke all on public.schema_migrations from anon, authenticated;
"""


def files(directory: Path = DIRECTORY) -> list[tuple[str, Path]]:
    """(version, path) of every up migration, in order. Two files with one number is a mistake worth stopping for."""
    found = sorted((m.group(1), p) for p in directory.glob("*.sql") if (m := FILE.match(p.name)) and not p.name.endswith(".down.sql"))
    versions = [v for v, _ in found]
    if len(set(versions)) != len(versions):
        raise SystemExit(f"Two migrations share a number in {directory}: {sorted(v for v in versions if versions.count(v) > 1)}")
    return found


def checksum(path: Path) -> str:
    """Line endings do not count: a Windows checkout and the Linux server must agree."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def connect(url: str | None = None):
    import psycopg

    # Keepalives and a TCP timeout: a dropped connection fails in seconds instead of hanging (seen on the pooler).
    return psycopg.connect(url or os.environ["DATABASE_URL"], autocommit=True, connect_timeout=15,
                           keepalives=1, keepalives_idle=10, keepalives_interval=5, keepalives_count=3, tcp_user_timeout=30000)


def applied(conn) -> dict[str, str]:
    conn.execute(TABLE)
    return dict(conn.execute("select version, checksum from public.schema_migrations").fetchall())


def up(conn, directory: Path = DIRECTORY) -> list[str]:
    """Apply every pending migration in order. Returns the versions applied."""
    done = applied(conn)
    changed = [p.name for v, p in files(directory) if v in done and done[v] != checksum(p)]
    if changed:
        raise SystemExit(f"Applied migrations were edited: {', '.join(changed)}. Put the change in a new numbered file instead.")
    ran = []
    for version, path in files(directory):
        if version in done:
            continue
        with conn.transaction():  # the whole file or nothing
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("insert into public.schema_migrations (version, name, checksum) values (%s, %s, %s)", (version, path.stem, checksum(path)))
        ran.append(version)
        print(f"applied {path.name}")
    return ran


def down(conn, directory: Path = DIRECTORY) -> str:
    """Undo the latest applied migration with its .down.sql file, in one transaction. Returns its version."""
    conn.execute(TABLE)
    latest = conn.execute("select version, name from public.schema_migrations order by version desc limit 1").fetchone()
    if latest is None:
        raise SystemExit("No migration has been applied.")
    undo = directory / f"{latest[1]}.down.sql"
    if not undo.exists():
        raise SystemExit(f"{latest[1]} cannot be undone: there is no {undo.name}. Write a new migration that reverses it.")
    with conn.transaction():
        conn.execute(undo.read_text(encoding="utf-8"))
        conn.execute("delete from public.schema_migrations where version = %s", (latest[0],))
    print(f"undid {latest[1]}")
    return latest[0]


def status(conn, directory: Path = DIRECTORY) -> list[str]:
    done = applied(conn)
    return [f"{'applied' if v in done else 'pending'}  {p.name}" + ("  (edited since applied)" if v in done and done[v] != checksum(p) else "")
            for v, p in files(directory)]


def main(argv: list[str]) -> None:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    command = argv[0] if argv else "up"
    with connect() as conn:
        if command == "up":
            print(f"{len(up(conn))} migration(s) applied.")
        elif command == "down":
            down(conn)
        elif command == "status":
            print("\n".join(status(conn)))
        else:
            raise SystemExit("Use: python -m app.migrate [up|status|down]")


if __name__ == "__main__":
    main(sys.argv[1:])

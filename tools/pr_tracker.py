#!/usr/bin/env python3
"""SQLite tracker for project PRs, motivations, and update log."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path("data/project_updates.db")
CURRENT_VERSION = 1

# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS motivations (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    detail     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'active'
               CHECK(status IN ('active','archived'))
);

CREATE TABLE IF NOT EXISTS pull_requests (
    id         INTEGER PRIMARY KEY,
    pr_number  INTEGER,
    title      TEXT NOT NULL,
    branch     TEXT,
    commit_sha TEXT,
    state      TEXT NOT NULL DEFAULT 'draft'
               CHECK(state IN ('draft','open','merged','closed')),
    opened_at  TEXT NOT NULL,
    closed_at  TEXT,
    notes      TEXT
);

CREATE TABLE IF NOT EXISTS pr_motivations (
    pr_id         INTEGER NOT NULL,
    motivation_id INTEGER NOT NULL,
    PRIMARY KEY (pr_id, motivation_id),
    FOREIGN KEY (pr_id)         REFERENCES pull_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (motivation_id) REFERENCES motivations(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS updates (
    id          INTEGER PRIMARY KEY,
    pr_id       INTEGER,
    summary     TEXT NOT NULL,
    details     TEXT,
    update_type TEXT NOT NULL DEFAULT 'note'
                CHECK(update_type IN ('note','decision','risk','test','status')),
    created_at  TEXT NOT NULL,
    FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_updates_pr_id      ON updates(pr_id);
CREATE INDEX IF NOT EXISTS idx_updates_created_at ON updates(created_at);
"""

# ── Migrations ────────────────────────────────────────────────────────────────
# Append-only list of (target_version, sql).  Never edit existing entries.

MIGRATIONS: list[tuple[int, str]] = [
    (1, _SCHEMA_V1),
    # (2, "ALTER TABLE motivations ADD COLUMN owner TEXT;"),
]


# ── Connection ────────────────────────────────────────────────────────────────

def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _schema_version(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row["value"]) if row else 0
    except sqlite3.OperationalError:
        return 0


def migrate(conn: sqlite3.Connection, *, verbose: bool = False) -> None:
    """Apply any outstanding migrations and update schema_version."""
    version = _schema_version(conn)
    applied = 0
    for target, sql in MIGRATIONS:
        if target > version:
            conn.executescript(sql)
            conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(target),),
            )
            conn.commit()
            conn.execute("PRAGMA foreign_keys = ON")   # executescript resets pragmas
            applied += 1
            version = target
    if applied and verbose:
        print(f"Schema migrated to v{version}.")


# ── Helpers ───────────────────────────────────────────────────────────────────

# merged is terminal — once merged a PR cannot transition to any other state.
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft":  {"open", "closed"},
    "open":   {"merged", "closed", "draft"},
    "merged": set(),
    "closed": {"open", "draft"},
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(conn: sqlite3.Connection, table: str, row_id: int, label: str) -> None:
    """Exit with a friendly message if row_id does not exist in table."""
    row = conn.execute(f"SELECT id FROM {table} WHERE id=?", (row_id,)).fetchone()  # noqa: S608
    if row is None:
        sys.exit(f"Error: {label} id={row_id} not found.")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_init(conn: sqlite3.Connection, _args) -> None:
    migrate(conn, verbose=True)
    print("Database ready.")


def cmd_add_motivation(conn: sqlite3.Connection, args) -> None:
    cur = conn.execute(
        "INSERT INTO motivations (title, detail, created_at) VALUES (?, ?, ?)",
        (args.title, args.detail, now()),
    )
    conn.commit()
    print(f"Motivation created  id={cur.lastrowid}")


def cmd_archive_motivation(conn: sqlite3.Connection, args) -> None:
    _require(conn, "motivations", args.id, "motivation")
    conn.execute("UPDATE motivations SET status='archived' WHERE id=?", (args.id,))
    conn.commit()
    print(f"Motivation id={args.id} archived.")


def cmd_add_pr(conn: sqlite3.Connection, args) -> None:
    for mid in args.motivation_ids or []:
        _require(conn, "motivations", mid, "motivation")
    cur = conn.execute(
        """INSERT INTO pull_requests
           (pr_number, title, branch, commit_sha, state, opened_at, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (args.pr_number, args.title, args.branch, args.commit_sha,
         args.state, now(), args.notes),
    )
    pr_id = cur.lastrowid
    for mid in args.motivation_ids or []:
        conn.execute(
            "INSERT OR IGNORE INTO pr_motivations (pr_id, motivation_id) VALUES (?, ?)",
            (pr_id, mid),
        )
    conn.commit()
    print(f"PR created  id={pr_id}")


def cmd_set_pr_state(conn: sqlite3.Connection, args) -> None:
    _require(conn, "pull_requests", args.id, "PR")
    row = conn.execute("SELECT state FROM pull_requests WHERE id=?", (args.id,)).fetchone()
    current = row["state"]
    if args.state not in _VALID_TRANSITIONS[current]:
        allowed = ", ".join(sorted(_VALID_TRANSITIONS[current])) or "none (terminal)"
        sys.exit(f"Error: cannot transition PR from '{current}' to '{args.state}'. "
                 f"Allowed: {allowed}.")
    closed_at = now() if args.state in ("merged", "closed") else None
    conn.execute(
        "UPDATE pull_requests SET state=?, closed_at=? WHERE id=?",
        (args.state, closed_at, args.id),
    )
    conn.commit()
    print(f"PR id={args.id} state → {args.state}")


def cmd_edit_pr(conn: sqlite3.Connection, args) -> None:
    _require(conn, "pull_requests", args.id, "PR")
    fields = {k: v for k, v in vars(args).items()
              if k not in ("id", "cmd") and v is not None}
    if not fields:
        sys.exit("Error: no fields to update — pass at least one option.")
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE pull_requests SET {sets} WHERE id=?",  # noqa: S608
        (*fields.values(), args.id),
    )
    conn.commit()
    print(f"PR id={args.id} updated: {', '.join(fields)}")


def cmd_edit_motivation(conn: sqlite3.Connection, args) -> None:
    _require(conn, "motivations", args.id, "motivation")
    fields = {k: v for k, v in vars(args).items()
              if k not in ("id", "cmd") and v is not None}
    if not fields:
        sys.exit("Error: no fields to update — pass at least one option.")
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE motivations SET {sets} WHERE id=?",  # noqa: S608
        (*fields.values(), args.id),
    )
    conn.commit()
    print(f"Motivation id={args.id} updated: {', '.join(fields)}")


def cmd_amend_update(conn: sqlite3.Connection, args) -> None:
    _require(conn, "updates", args.id, "update")
    fields = {k: v for k, v in vars(args).items()
              if k not in ("id", "cmd") and v is not None}
    if not fields:
        sys.exit("Error: no fields to update — pass at least one option.")
    sets = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE updates SET {sets} WHERE id=?",  # noqa: S608
        (*fields.values(), args.id),
    )
    conn.commit()
    print(f"Update id={args.id} amended: {', '.join(fields)}")


def cmd_add_update(conn: sqlite3.Connection, args) -> None:
    if args.pr_id is not None:
        _require(conn, "pull_requests", args.pr_id, "PR")
    cur = conn.execute(
        "INSERT INTO updates (pr_id, summary, details, update_type, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (args.pr_id, args.summary, args.details, args.update_type, now()),
    )
    conn.commit()
    print(f"Update created  id={cur.lastrowid}")


def cmd_list_prs(conn: sqlite3.Connection, args) -> None:
    base = """
    SELECT p.id, p.pr_number, p.title, p.state, p.branch, p.commit_sha,
           p.opened_at, p.closed_at,
           GROUP_CONCAT(m.title, '; ') AS motivations
    FROM pull_requests p
    LEFT JOIN pr_motivations pm ON pm.pr_id = p.id
    LEFT JOIN motivations m     ON m.id = pm.motivation_id
    {where}
    GROUP BY p.id ORDER BY p.id DESC
    """
    where = "WHERE p.state=?" if args.state else ""
    params: tuple = (args.state,) if args.state else ()
    rows = conn.execute(base.format(where=where), params).fetchall()

    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2))
        return

    if not rows:
        print("No PRs found.")
        return
    for r in rows:
        print(f"  [{r['id']}] PR#{r['pr_number'] or '-'}  {r['title']}  state={r['state']}"
              f"  branch={r['branch'] or '-'}")
        if r["motivations"]:
            print(f"         motivations: {r['motivations']}")


def cmd_report(conn: sqlite3.Connection, args) -> None:
    motivations = conn.execute(
        "SELECT id, title, status, created_at FROM motivations ORDER BY id DESC"
    ).fetchall()

    prs = conn.execute("""
    SELECT p.id, p.pr_number, p.title, p.state, p.branch, p.commit_sha,
           p.opened_at, p.closed_at, p.notes,
           GROUP_CONCAT(m.title, '; ') AS motivations
    FROM pull_requests p
    LEFT JOIN pr_motivations pm ON pm.pr_id = p.id
    LEFT JOIN motivations m     ON m.id = pm.motivation_id
    GROUP BY p.id ORDER BY p.id DESC
    """).fetchall()

    updates = conn.execute("""
    SELECT u.id, u.update_type, u.summary, u.details, u.created_at,
           p.title AS pr_title
    FROM updates u
    LEFT JOIN pull_requests p ON p.id = u.pr_id
    ORDER BY u.id DESC LIMIT 20
    """).fetchall()

    if args.json:
        print(json.dumps({
            "motivations":    [dict(r) for r in motivations],
            "pull_requests":  [dict(r) for r in prs],
            "recent_updates": [dict(r) for r in updates],
        }, indent=2))
        return

    print("\n── Motivations ──────────────────────────────────────────────────")
    for r in motivations:
        print(f"  [{r['id']}] {r['title']} ({r['status']}) @ {r['created_at']}")

    print("\n── Pull Requests ────────────────────────────────────────────────")
    for r in prs:
        print(f"  [{r['id']}] PR#{r['pr_number'] or '-'}  {r['title']}"
              f"  state={r['state']}  branch={r['branch'] or '-'}")
        if r["motivations"]:
            print(f"         motivations: {r['motivations']}")

    print("\n── Recent Updates (last 20) ─────────────────────────────────────")
    for r in updates:
        print(f"  [{r['id']}] {r['update_type']}: {r['summary']}"
              f"  (PR={r['pr_title'] or '-'}) @ {r['created_at']}")


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Track PR motivations and updates in SQLite.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help="Path to SQLite database (default: data/project_updates.db)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Initialise / migrate the database schema")

    p_m = sub.add_parser("add-motivation", help="Record a new motivation")
    p_m.add_argument("title")
    p_m.add_argument("detail")

    p_am = sub.add_parser("archive-motivation", help="Archive a motivation by id")
    p_am.add_argument("id", type=int)

    p_pr = sub.add_parser("add-pr", help="Record a new PR")
    p_pr.add_argument("title")
    p_pr.add_argument("--pr-number", type=int)
    p_pr.add_argument("--branch")
    p_pr.add_argument("--commit-sha")
    p_pr.add_argument("--state", default="draft",
                      choices=["draft", "open", "merged", "closed"])
    p_pr.add_argument("--notes")
    p_pr.add_argument("--motivation-ids", type=int, nargs="*",
                      metavar="ID", help="Link existing motivation IDs")

    p_sps = sub.add_parser("set-pr-state", help="Transition a PR's lifecycle state")
    p_sps.add_argument("id", type=int)
    p_sps.add_argument("state", choices=["draft", "open", "merged", "closed"])

    p_epr = sub.add_parser("edit-pr", help="Edit fields on an existing PR")
    p_epr.add_argument("id", type=int)
    p_epr.add_argument("--title")
    p_epr.add_argument("--pr-number", type=int)
    p_epr.add_argument("--branch")
    p_epr.add_argument("--commit-sha")
    p_epr.add_argument("--notes")

    p_em = sub.add_parser("edit-motivation", help="Edit title or detail of a motivation")
    p_em.add_argument("id", type=int)
    p_em.add_argument("--title")
    p_em.add_argument("--detail")

    p_au = sub.add_parser("amend-update", help="Amend an existing update entry")
    p_au.add_argument("id", type=int)
    p_au.add_argument("--summary")
    p_au.add_argument("--details")
    p_au.add_argument("--update-type", choices=["note", "decision", "risk", "test", "status"])

    p_u = sub.add_parser("add-update", help="Append a chronological update entry")
    p_u.add_argument("summary")
    p_u.add_argument("--pr-id", type=int)
    p_u.add_argument("--details")
    p_u.add_argument("--update-type", default="note",
                     choices=["note", "decision", "risk", "test", "status"])

    p_lp = sub.add_parser("list-prs", help="List PRs, optionally filtered by state")
    p_lp.add_argument("--state", choices=["draft", "open", "merged", "closed"])
    p_lp.add_argument("--json", action="store_true")

    p_r = sub.add_parser("report", help="Print full project state report")
    p_r.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    return parser


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd != "init":
            migrate(conn)
        dispatch = {
            "init":               cmd_init,
            "add-motivation":     cmd_add_motivation,
            "archive-motivation": cmd_archive_motivation,
            "edit-motivation":    cmd_edit_motivation,
            "add-pr":             cmd_add_pr,
            "set-pr-state":       cmd_set_pr_state,
            "edit-pr":            cmd_edit_pr,
            "add-update":         cmd_add_update,
            "amend-update":       cmd_amend_update,
            "list-prs":           cmd_list_prs,
            "report":             cmd_report,
        }
        dispatch[args.cmd](conn, args)
    except sqlite3.IntegrityError as exc:
        sys.exit(f"Database constraint error: {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

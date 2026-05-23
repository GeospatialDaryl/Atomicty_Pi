#!/usr/bin/env python3
"""Simple SQLite tracker for project updates, PRs, and motivations."""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path("data/project_updates.db")

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS motivations (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','archived'))
);

CREATE TABLE IF NOT EXISTS pull_requests (
    id INTEGER PRIMARY KEY,
    pr_number INTEGER,
    title TEXT NOT NULL,
    branch TEXT,
    commit_sha TEXT,
    state TEXT NOT NULL DEFAULT 'draft' CHECK(state IN ('draft','open','merged','closed')),
    opened_at TEXT NOT NULL,
    closed_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS pr_motivations (
    pr_id INTEGER NOT NULL,
    motivation_id INTEGER NOT NULL,
    PRIMARY KEY (pr_id, motivation_id),
    FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (motivation_id) REFERENCES motivations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS updates (
    id INTEGER PRIMARY KEY,
    pr_id INTEGER,
    summary TEXT NOT NULL,
    details TEXT,
    update_type TEXT NOT NULL DEFAULT 'note' CHECK(update_type IN ('note','decision','risk','test','status')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (pr_id) REFERENCES pull_requests(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_updates_pr_id ON updates(pr_id);
CREATE INDEX IF NOT EXISTS idx_updates_created_at ON updates(created_at);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def cmd_init(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
    print("Initialized schema.")


def cmd_add_motivation(conn, args):
    cur = conn.execute(
        "INSERT INTO motivations (title, detail, created_at, status) VALUES (?, ?, ?, 'active')",
        (args.title, args.detail, now()),
    )
    conn.commit()
    print(f"Created motivation id={cur.lastrowid}")


def cmd_add_pr(conn, args):
    cur = conn.execute(
        """INSERT INTO pull_requests
        (pr_number, title, branch, commit_sha, state, opened_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (args.pr_number, args.title, args.branch, args.commit_sha, args.state, now(), args.notes),
    )
    pr_id = cur.lastrowid
    for mid in args.motivation_ids or []:
        conn.execute("INSERT OR IGNORE INTO pr_motivations (pr_id, motivation_id) VALUES (?, ?)", (pr_id, mid))
    conn.commit()
    print(f"Created PR id={pr_id}")


def cmd_add_update(conn, args):
    cur = conn.execute(
        "INSERT INTO updates (pr_id, summary, details, update_type, created_at) VALUES (?, ?, ?, ?, ?)",
        (args.pr_id, args.summary, args.details, args.update_type, now()),
    )
    conn.commit()
    print(f"Created update id={cur.lastrowid}")


def cmd_report(conn, _args):
    print("\nMotivations")
    for row in conn.execute("SELECT id, title, status, created_at FROM motivations ORDER BY id DESC"):
        print(f"  [{row['id']}] {row['title']} ({row['status']}) @ {row['created_at']}")

    print("\nPRs")
    q = """
    SELECT p.id, p.pr_number, p.title, p.state, p.branch, p.commit_sha,
           GROUP_CONCAT(m.title, '; ') AS motivations
    FROM pull_requests p
    LEFT JOIN pr_motivations pm ON pm.pr_id = p.id
    LEFT JOIN motivations m ON m.id = pm.motivation_id
    GROUP BY p.id
    ORDER BY p.id DESC
    """
    for row in conn.execute(q):
        print(
            f"  [{row['id']}] PR#{row['pr_number'] or '-'} {row['title']} "
            f"state={row['state']} branch={row['branch'] or '-'} motivations={row['motivations'] or '-'}"
        )

    print("\nRecent Updates")
    q2 = """
    SELECT u.id, u.update_type, u.summary, u.created_at, p.title AS pr_title
    FROM updates u
    LEFT JOIN pull_requests p ON p.id = u.pr_id
    ORDER BY u.id DESC
    LIMIT 20
    """
    for row in conn.execute(q2):
        print(f"  [{row['id']}] {row['update_type']}: {row['summary']} (PR={row['pr_title'] or '-'}) @ {row['created_at']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Track PR motivations and updates in SQLite.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Path to sqlite database file")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_m = sub.add_parser("add-motivation")
    p_m.add_argument("title")
    p_m.add_argument("detail")

    p_pr = sub.add_parser("add-pr")
    p_pr.add_argument("title")
    p_pr.add_argument("--pr-number", type=int)
    p_pr.add_argument("--branch")
    p_pr.add_argument("--commit-sha")
    p_pr.add_argument("--state", default="draft", choices=["draft", "open", "merged", "closed"])
    p_pr.add_argument("--notes")
    p_pr.add_argument("--motivation-ids", type=int, nargs="*")

    p_u = sub.add_parser("add-update")
    p_u.add_argument("summary")
    p_u.add_argument("--pr-id", type=int)
    p_u.add_argument("--details")
    p_u.add_argument("--update-type", default="note", choices=["note", "decision", "risk", "test", "status"])

    sub.add_parser("report")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    conn = connect(args.db)
    try:
        if args.cmd == "init":
            cmd_init(conn)
        elif args.cmd == "add-motivation":
            cmd_add_motivation(conn, args)
        elif args.cmd == "add-pr":
            cmd_add_pr(conn, args)
        elif args.cmd == "add-update":
            cmd_add_update(conn, args)
        elif args.cmd == "report":
            cmd_report(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

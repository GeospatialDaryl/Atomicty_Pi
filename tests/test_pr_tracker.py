"""Tests for tools/pr_tracker.py"""

from __future__ import annotations

import json
import sqlite3

import pytest

from pr_tracker import (
    CURRENT_VERSION,
    cmd_add_motivation,
    cmd_add_pr,
    cmd_add_update,
    cmd_amend_update,
    cmd_archive_motivation,
    cmd_edit_motivation,
    cmd_edit_pr,
    cmd_list_prs,
    cmd_report,
    cmd_set_pr_state,
    connect,
    migrate,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path):
    conn = connect(tmp_path / "test.db")
    migrate(conn)
    yield conn
    conn.close()


# Minimal arg-namespace helpers — avoids importing argparse in every test.

class _M:
    """Motivation args."""
    def __init__(self, title="T", detail="D"):
        self.title = title
        self.detail = detail


class _PR:
    """PR args."""
    def __init__(self, title="PR", *, state="open", motivation_ids=None):
        self.title = title
        self.pr_number = None
        self.branch = None
        self.commit_sha = None
        self.state = state
        self.notes = None
        self.motivation_ids = motivation_ids or []


class _Update:
    """Update args."""
    def __init__(self, summary="s", *, pr_id=None, update_type="note"):
        self.summary = summary
        self.pr_id = pr_id
        self.details = None
        self.update_type = update_type


class _SetState:
    def __init__(self, pr_id, state):
        self.id = pr_id
        self.state = state


class _ArchiveMotivation:
    def __init__(self, motivation_id):
        self.id = motivation_id


class _EditPR:
    def __init__(self, pr_id, **kwargs):
        self.id = pr_id
        self.cmd = "edit-pr"
        self.title = kwargs.get("title")
        self.pr_number = kwargs.get("pr_number")
        self.branch = kwargs.get("branch")
        self.commit_sha = kwargs.get("commit_sha")
        self.notes = kwargs.get("notes")


class _EditMotivation:
    def __init__(self, motivation_id, **kwargs):
        self.id = motivation_id
        self.cmd = "edit-motivation"
        self.title = kwargs.get("title")
        self.detail = kwargs.get("detail")


class _AmendUpdate:
    def __init__(self, update_id, **kwargs):
        self.id = update_id
        self.cmd = "amend-update"
        self.summary = kwargs.get("summary")
        self.details = kwargs.get("details")
        self.update_type = kwargs.get("update_type")


class _ListPRs:
    def __init__(self, state=None, *, as_json=False):
        self.state = state
        self.json = as_json


class _Report:
    def __init__(self, *, as_json=False):
        self.json = as_json


# ── Migration / schema ────────────────────────────────────────────────────────

def test_migration_sets_version(db):
    row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert int(row["value"]) == CURRENT_VERSION


def test_migration_is_idempotent(db):
    migrate(db)  # second call should be a no-op
    row = db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    assert int(row["value"]) == CURRENT_VERSION


def test_fk_enforcement(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO pr_motivations (pr_id, motivation_id) VALUES (999, 999)"
        )


def test_check_pr_state_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO pull_requests (title, state, opened_at) "
            "VALUES ('X', 'invalid', 'now')"
        )


def test_check_update_type_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO updates (summary, update_type, created_at) "
            "VALUES ('X', 'bad_type', 'now')"
        )


def test_check_motivation_status_constraint(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO motivations (title, detail, created_at, status) "
            "VALUES ('T', 'D', 'now', 'pending')"
        )


# ── Motivations ───────────────────────────────────────────────────────────────

def test_add_motivation_creates_record(db):
    cmd_add_motivation(db, _M("Goal", "Why"))
    rows = db.execute("SELECT * FROM motivations").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "Goal"
    assert rows[0]["status"] == "active"


def test_archive_motivation(db):
    cmd_add_motivation(db, _M())
    cmd_archive_motivation(db, _ArchiveMotivation(1))
    row = db.execute("SELECT status FROM motivations WHERE id=1").fetchone()
    assert row["status"] == "archived"


def test_archive_motivation_not_found(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_archive_motivation(db, _ArchiveMotivation(999))


# ── Pull Requests ─────────────────────────────────────────────────────────────

def test_add_pr_basic(db):
    cmd_add_pr(db, _PR("My PR", state="draft"))
    row = db.execute("SELECT * FROM pull_requests WHERE id=1").fetchone()
    assert row["title"] == "My PR"
    assert row["state"] == "draft"


def test_add_pr_links_motivations(db):
    cmd_add_motivation(db, _M())
    cmd_add_pr(db, _PR(motivation_ids=[1]))
    link = db.execute(
        "SELECT * FROM pr_motivations WHERE pr_id=1 AND motivation_id=1"
    ).fetchone()
    assert link is not None


def test_add_pr_rejects_missing_motivation(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_add_pr(db, _PR(motivation_ids=[999]))


def test_set_pr_state_open_to_merged(db):
    cmd_add_pr(db, _PR(state="open"))
    cmd_set_pr_state(db, _SetState(1, "merged"))
    row = db.execute("SELECT state, closed_at FROM pull_requests WHERE id=1").fetchone()
    assert row["state"] == "merged"
    assert row["closed_at"] is not None


def test_set_pr_state_open_does_not_set_closed_at(db):
    cmd_add_pr(db, _PR(state="draft"))
    cmd_set_pr_state(db, _SetState(1, "open"))
    row = db.execute("SELECT closed_at FROM pull_requests WHERE id=1").fetchone()
    assert row["closed_at"] is None


def test_set_pr_state_not_found(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_set_pr_state(db, _SetState(999, "open"))


def test_list_prs_unfiltered(db):
    cmd_add_pr(db, _PR("A", state="open"))
    cmd_add_pr(db, _PR("B", state="merged"))
    rows = db.execute("SELECT id FROM pull_requests").fetchall()
    assert len(rows) == 2


def test_list_prs_filtered_by_state(db, capsys):
    cmd_add_pr(db, _PR("Open", state="open"))
    cmd_add_pr(db, _PR("Merged", state="merged"))
    cmd_list_prs(db, _ListPRs(state="open"))
    out = capsys.readouterr().out
    assert "Open" in out
    assert "Merged" not in out


def test_list_prs_json(db, capsys):
    cmd_add_pr(db, _PR("PR1"))
    capsys.readouterr()  # discard "PR created" line before capturing JSON
    cmd_list_prs(db, _ListPRs(as_json=True))
    data = json.loads(capsys.readouterr().out)
    assert isinstance(data, list)
    assert data[0]["title"] == "PR1"


# ── Updates ───────────────────────────────────────────────────────────────────

def test_add_update_standalone(db):
    cmd_add_update(db, _Update("Standalone note"))
    row = db.execute("SELECT * FROM updates WHERE id=1").fetchone()
    assert row["summary"] == "Standalone note"
    assert row["pr_id"] is None


def test_add_update_linked_to_pr(db):
    cmd_add_pr(db, _PR())
    cmd_add_update(db, _Update("Linked", pr_id=1, update_type="decision"))
    row = db.execute("SELECT update_type, pr_id FROM updates WHERE id=1").fetchone()
    assert row["update_type"] == "decision"
    assert row["pr_id"] == 1


def test_add_update_rejects_missing_pr(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_add_update(db, _Update("X", pr_id=999))


# ── Report ────────────────────────────────────────────────────────────────────

def test_report_text(db, capsys):
    cmd_add_motivation(db, _M("Goal", "Why"))
    cmd_add_pr(db, _PR("PR1", motivation_ids=[1]))
    cmd_add_update(db, _Update("Note1", pr_id=1))
    cmd_report(db, _Report())
    out = capsys.readouterr().out
    assert "Goal" in out
    assert "PR1" in out
    assert "Note1" in out


def test_report_json_structure(db, capsys):
    cmd_add_motivation(db, _M())
    cmd_add_pr(db, _PR())
    cmd_add_update(db, _Update())
    capsys.readouterr()  # discard setup prints before capturing JSON
    cmd_report(db, _Report(as_json=True))
    data = json.loads(capsys.readouterr().out)
    assert "motivations" in data
    assert "pull_requests" in data
    assert "recent_updates" in data


def test_report_json_empty_db(db, capsys):
    cmd_report(db, _Report(as_json=True))
    data = json.loads(capsys.readouterr().out)
    assert data["motivations"] == []
    assert data["pull_requests"] == []


# ── State transition validation ───────────────────────────────────────────────

def test_valid_transition_draft_to_open(db):
    cmd_add_pr(db, _PR(state="draft"))
    cmd_set_pr_state(db, _SetState(1, "open"))
    row = db.execute("SELECT state FROM pull_requests WHERE id=1").fetchone()
    assert row["state"] == "open"


def test_valid_transition_open_to_merged(db):
    cmd_add_pr(db, _PR(state="open"))
    cmd_set_pr_state(db, _SetState(1, "merged"))
    row = db.execute("SELECT state FROM pull_requests WHERE id=1").fetchone()
    assert row["state"] == "merged"


def test_invalid_transition_merged_is_terminal(db):
    cmd_add_pr(db, _PR(state="open"))
    cmd_set_pr_state(db, _SetState(1, "merged"))
    with pytest.raises(SystemExit, match="terminal"):
        cmd_set_pr_state(db, _SetState(1, "open"))


def test_invalid_transition_draft_to_merged(db):
    cmd_add_pr(db, _PR(state="draft"))
    with pytest.raises(SystemExit, match="cannot transition"):
        cmd_set_pr_state(db, _SetState(1, "merged"))


def test_valid_transition_closed_to_open(db):
    cmd_add_pr(db, _PR(state="open"))
    cmd_set_pr_state(db, _SetState(1, "closed"))
    cmd_set_pr_state(db, _SetState(1, "open"))
    row = db.execute("SELECT state FROM pull_requests WHERE id=1").fetchone()
    assert row["state"] == "open"


# ── edit-pr ───────────────────────────────────────────────────────────────────

def test_edit_pr_updates_notes(db):
    cmd_add_pr(db, _PR("Original"))
    cmd_edit_pr(db, _EditPR(1, notes="Updated notes"))
    row = db.execute("SELECT notes FROM pull_requests WHERE id=1").fetchone()
    assert row["notes"] == "Updated notes"


def test_edit_pr_updates_multiple_fields(db):
    cmd_add_pr(db, _PR("Old title"))
    cmd_edit_pr(db, _EditPR(1, title="New title", branch="feature/x"))
    row = db.execute("SELECT title, branch FROM pull_requests WHERE id=1").fetchone()
    assert row["title"] == "New title"
    assert row["branch"] == "feature/x"


def test_edit_pr_no_fields_exits(db):
    cmd_add_pr(db, _PR())
    with pytest.raises(SystemExit, match="no fields"):
        cmd_edit_pr(db, _EditPR(1))


def test_edit_pr_not_found(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_edit_pr(db, _EditPR(999, notes="x"))


# ── edit-motivation ───────────────────────────────────────────────────────────

def test_edit_motivation_updates_title(db):
    cmd_add_motivation(db, _M("Old", "D"))
    cmd_edit_motivation(db, _EditMotivation(1, title="New"))
    row = db.execute("SELECT title FROM motivations WHERE id=1").fetchone()
    assert row["title"] == "New"


def test_edit_motivation_updates_detail(db):
    cmd_add_motivation(db, _M("T", "Old detail"))
    cmd_edit_motivation(db, _EditMotivation(1, detail="New detail"))
    row = db.execute("SELECT detail FROM motivations WHERE id=1").fetchone()
    assert row["detail"] == "New detail"


def test_edit_motivation_no_fields_exits(db):
    cmd_add_motivation(db, _M())
    with pytest.raises(SystemExit, match="no fields"):
        cmd_edit_motivation(db, _EditMotivation(1))


def test_edit_motivation_not_found(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_edit_motivation(db, _EditMotivation(999, title="x"))


# ── amend-update ──────────────────────────────────────────────────────────────

def test_amend_update_changes_summary(db):
    cmd_add_update(db, _Update("Original"))
    cmd_amend_update(db, _AmendUpdate(1, summary="Corrected"))
    row = db.execute("SELECT summary FROM updates WHERE id=1").fetchone()
    assert row["summary"] == "Corrected"


def test_amend_update_changes_type(db):
    cmd_add_update(db, _Update("Note", update_type="note"))
    cmd_amend_update(db, _AmendUpdate(1, update_type="decision"))
    row = db.execute("SELECT update_type FROM updates WHERE id=1").fetchone()
    assert row["update_type"] == "decision"


def test_amend_update_no_fields_exits(db):
    cmd_add_update(db, _Update())
    with pytest.raises(SystemExit, match="no fields"):
        cmd_amend_update(db, _AmendUpdate(1))


def test_amend_update_not_found(db):
    with pytest.raises(SystemExit, match="not found"):
        cmd_amend_update(db, _AmendUpdate(999, summary="x"))

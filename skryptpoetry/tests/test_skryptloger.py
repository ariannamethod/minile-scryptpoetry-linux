import sys
from pathlib import Path
import sqlite3

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import skryptloger  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db = tmp_path / "test.sqlite3"
    monkeypatch.setattr(skryptloger, "DB_PATH", db)
    skryptloger.init_db()
    return db


def test_init_db_creates_tables(temp_db):
    assert temp_db.exists()
    with sqlite3.connect(temp_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"logs", "used_scripts", "trained_files"} <= tables


def test_log_interaction_and_script_used(temp_db):
    skryptloger.log_interaction("hi", "test_script", 1.0, 2.0, 3.0)
    with sqlite3.connect(skryptloger.DB_PATH) as conn:
        row = conn.execute(
            "SELECT message, script, entropy, perplexity, resonance FROM logs"
        ).fetchone()
    assert row == ("hi", "test_script", 1.0, 2.0, 3.0)
    assert skryptloger.script_used("test_script")
    assert not skryptloger.script_used("other")


def test_log_trained_file_and_was_trained(temp_db, tmp_path):
    file_path = tmp_path / "file.txt"
    sha256 = "abc123"
    skryptloger.log_trained_file(file_path, sha256)
    assert skryptloger.was_trained(file_path, sha256)
    assert not skryptloger.was_trained(file_path, "different")

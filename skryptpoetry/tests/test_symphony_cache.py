import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import symphony  # noqa: E402


def test_cache_returns_same_content_when_file_unchanged(tmp_path, monkeypatch):
    test_file = tmp_path / "data.txt"
    test_file.write_text("hello")

    monkeypatch.setattr(symphony, "_CACHE", {})

    first = symphony._load_file(test_file)
    assert first == "hello"

    def fail_read(self, *a, **k):  # pragma: no cover - should not run
        raise RuntimeError("read should not be called")

    monkeypatch.setattr(Path, "read_text", fail_read)

    second = symphony._load_file(test_file)
    assert second == "hello"


def test_cache_refreshes_when_mtime_changes(tmp_path, monkeypatch):
    test_file = tmp_path / "data.txt"
    test_file.write_text("one")

    monkeypatch.setattr(symphony, "_CACHE", {})

    calls = []
    original = Path.read_text

    def spy(self, *args, **kwargs):
        calls.append(1)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy)

    first = symphony._load_file(test_file)
    assert first == "one"
    assert len(calls) == 1

    time.sleep(1)
    test_file.write_text("two")

    second = symphony._load_file(test_file)
    assert second == "two"
    assert len(calls) == 2


def test_cache_handles_unreadable_file(tmp_path, monkeypatch):
    test_file = tmp_path / "data.txt"
    test_file.write_text("content")

    monkeypatch.setattr(symphony, "_CACHE", {})

    def boom(self, *a, **k):
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", boom)

    result = symphony._load_file(test_file)
    assert result == ""
    assert test_file not in symphony._CACHE

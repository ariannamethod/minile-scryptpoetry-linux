import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import skryptloger  # noqa: E402
from skryptrainer import SkryptTrainer  # noqa: E402


def _trainer(tmp_path, monkeypatch, **kwargs):
    monkeypatch.setattr(skryptloger, "DB_PATH", tmp_path / "db.sqlite3")
    return SkryptTrainer(datasets=[tmp_path], **kwargs)


def test_concurrent_scan_and_train(tmp_path, monkeypatch):
    trainer = _trainer(tmp_path, monkeypatch)
    (tmp_path / "file.txt").write_text("data")

    calls = []

    def fake_train(path):
        time.sleep(0.01)
        calls.append(path)

    monkeypatch.setattr(trainer, "_train_file", fake_train)

    threads = []
    for _ in range(5):
        threads.append(threading.Thread(target=trainer.scan_and_train))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls == [tmp_path / "file.txt"]


def test_custom_filters(tmp_path, monkeypatch):
    trainer = _trainer(
        tmp_path,
        monkeypatch,
        allowed_extensions={".xyz"},
        excluded_parts={"skip"},
    )

    (tmp_path / "good.xyz").write_text("data")
    (tmp_path / "bad.txt").write_text("data")
    (tmp_path / "skip").mkdir()
    (tmp_path / "skip" / "also.xyz").write_text("data")

    calls = []

    def fake_train(path):
        calls.append(path)

    monkeypatch.setattr(trainer, "_train_file", fake_train)

    trainer.scan_and_train()

    assert calls == [tmp_path / "good.xyz"]


def test_scan_and_train_with_train_on_text(tmp_path, monkeypatch):
    trainer = _trainer(tmp_path, monkeypatch)
    (tmp_path / "file.txt").write_text("data")

    calls = []

    def fake_train(path):
        time.sleep(0.01)
        calls.append(path)

    monkeypatch.setattr(trainer, "_train_file", fake_train)

    def train_on_text():
        trainer.train_on_text("extra")

    threads = [
        threading.Thread(target=trainer.scan_and_train),
        threading.Thread(target=train_on_text),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls == [tmp_path / "file.txt"]


def test_train_on_text_async_during_scan(tmp_path, monkeypatch):
    class DummyModel:
        def __init__(self):
            self.calls = []
            self.extra_event = threading.Event()

        def train(self, text):
            self.calls.append(text)
            if text == "extra":
                self.extra_event.set()

    model = DummyModel()
    trainer = _trainer(tmp_path, monkeypatch, model=model)
    (tmp_path / "file.txt").write_text("data")

    scan_thread = threading.Thread(target=trainer.scan_and_train)
    scan_thread.start()

    trainer.train_on_text_async("extra")

    scan_thread.join()
    assert model.extra_event.wait(1)

    assert model.calls.count("extra") == 1
    assert model.calls.count("data") == 1
    assert len(model.calls) == 2

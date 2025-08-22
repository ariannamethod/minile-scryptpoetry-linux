import hashlib
import threading
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from skryptloger import init_db, log_trained_file, was_trained

# Default filters for eligible training files
ALLOWED_EXTENSIONS = {".md", ".txt", ".json", ".csv"}
EXCLUDED_PARTS = {".git"}


class SkryptTrainer:
    """Lightweight trainer that scans directories and avoids retraining."""

    def __init__(
        self,
        datasets: Iterable[str] = (".", "datasets", "tongue"),
        model: Optional[Callable[[str], None]] = None,
        allowed_extensions: Optional[Sequence[str]] = None,
        excluded_parts: Optional[Sequence[str]] = None,
    ) -> None:
        """Create a trainer.

        Parameters
        ----------
        datasets:
            Iterable of directory paths to scan for training files.
        model:
            Callable that performs training on provided text.
        allowed_extensions:
            File extensions eligible for training. Defaults to
            :data:`ALLOWED_EXTENSIONS`.
        excluded_parts:
            Path components to ignore while scanning. Defaults to
            :data:`EXCLUDED_PARTS`.
        """

        self.dirs = [Path(p) for p in datasets]
        self._scan_lock = threading.Lock()
        self.model = model
        self.allowed_extensions = set(allowed_extensions or ALLOWED_EXTENSIONS)
        self.excluded_parts = set(excluded_parts or EXCLUDED_PARTS)
        init_db()

    def _file_hash(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    def _eligible_files(self) -> Iterable[Path]:
        for directory in self.dirs:
            if not directory.exists():
                continue
            for file in directory.rglob("*"):
                if any(part in self.excluded_parts for part in file.parts):
                    continue
                if file.is_file() and file.suffix.lower() in self.allowed_extensions:
                    yield file

    def _train_text(self, text: str) -> None:
        """Feed raw text to the model if one is provided."""
        if not self.model:
            return
        if hasattr(self.model, "train") and callable(
            getattr(self.model, "train")
        ):
            self.model.train(text)
        else:
            self.model(text)

    def _train_file(self, path: Path) -> None:
        """Load file contents and train the model."""
        text = path.read_text(encoding="utf-8")
        self._train_text(text)

    def _scan_and_train(self) -> None:
        for file in self._eligible_files():
            sha = self._file_hash(file)
            if not was_trained(file, sha):
                self._train_file(file)
                log_trained_file(file, sha)

    def scan_and_train(self) -> None:
        with self._scan_lock:
            self._scan_and_train()

    def train_async(self) -> None:
        threading.Thread(target=self.scan_and_train, daemon=True).start()

    def train_on_text(self, text: str) -> None:
        """Train directly on provided text without rescanning files."""
        with self._scan_lock:
            self._train_text(text)

    def train_on_text_async(self, text: str) -> None:
        threading.Thread(
            target=self.train_on_text, args=(text,), daemon=True
        ).start()

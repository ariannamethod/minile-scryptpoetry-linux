from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, Iterable


class State:
    """Monitor repository files and refresh RAG memory on changes."""

    def __init__(
        self,
        root: str | Path | None = None,
        targets: Iterable[str] | None = None,
        interval: float = 1.0,
    ) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[1])
        self.interval = interval
        self.targets = [
            self.root / t
            for t in (
                targets
                or [
                    "README.md",
                    "datasets/Arianna-Method-v2.9.md",
                    "index.html",
                    "arianna_core/le_persona_prompt.md",
                    "datasets",
                ]
            )
        ]
        self.file_hashes = self._scan_repo()

        thread = threading.Thread(target=self._watch_loop, daemon=True)
        thread.start()

    # --- public / helper methods -------------------------------------------------
    def _hash_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _scan_repo(self) -> Dict[str, str]:
        """Return mapping of relative file paths to SHA256 digests."""
        hashes: Dict[str, str] = {}
        for target in self.targets:
            if target.is_dir():
                for file in target.rglob("*"):
                    if file.is_file():
                        rel = file.relative_to(self.root)
                        hashes[str(rel)] = self._hash_file(file)
            elif target.is_file():
                rel = target.relative_to(self.root)
                hashes[str(rel)] = self._hash_file(target)
        return hashes

    def _watch_loop(self) -> None:
        """Poll the repository and refresh caches on changes."""
        while True:
            current = self._scan_repo()
            if current != self.file_hashes:
                self.file_hashes = current
                self._ingest_story_once()
                self._ingest_datasets_once()
                self._cache_chunks()
            time.sleep(self.interval)

    # --- hooks for RAG updates ---------------------------------------------------
    def _ingest_story_once(self) -> None:  # pragma: no cover - overridable hook
        """Ingest the main story files into the RAG store once."""
        return None

    def _ingest_datasets_once(self) -> None:  # pragma: no cover - overridable hook
        """Ingest dataset files into the RAG store once."""
        return None

    def _cache_chunks(self) -> None:  # pragma: no cover - overridable hook
        """Refresh cached vector chunks used for retrieval."""
        return None

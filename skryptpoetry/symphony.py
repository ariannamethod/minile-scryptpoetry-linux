import logging
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Union

from skryptmetrics import entropy, perplexity, resonance
from skryptloger import init_db, log_interaction, script_used
from skryptrainer import SkryptTrainer


_CACHE: Dict[Path, Tuple[float, str]] = {}


def _load_file(path: Path) -> str:
    """Return cached file contents, refreshing only when changed."""
    if not path.exists():
        return ""
    mtime = path.stat().st_mtime
    cached = _CACHE.get(path)
    if cached and cached[0] == mtime:
        return cached[1]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logging.error("_load_file: failed to read %s: %s", path, exc)
        return ""
    _CACHE[path] = (mtime, text)
    return text


def retrieve(query: str, documents: Iterable[Union[Path, str]]) -> str:
    """Return the document text that resonates most with the query."""
    best_text = ""
    best_score = -1.0
    for doc in documents:
        if isinstance(doc, Path):
            text = _load_file(doc)
            if not text:
                continue
        else:
            text = doc
        score = resonance(query, text)
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


class Symphony:
    """Minimal interactive agent operating on small datasets."""

    def __init__(self,
                 dataset_path: str = 'datasets/dataset01.md',
                 scripts_path: str = 'tongue/prelanguage.md') -> None:
        init_db()
        self.dataset_path = Path(dataset_path)
        self.scripts_path = Path(scripts_path)
        self.trainer = SkryptTrainer()
        # Убираем медленную инициализацию обучения
        self.dataset_text = _load_file(self.dataset_path)
        self.scripts_text = _load_file(self.scripts_path)
        self.user_messages: List[str] = []

    def _available_scripts(self) -> List[str]:
        if not self.scripts_path.exists():
            msg = f"Scripts file not found: {self.scripts_path}"
            logging.warning(msg)
            raise FileNotFoundError(msg)

        self.scripts_text = _load_file(self.scripts_path)
        if not self.scripts_text.strip():
            msg = f"Scripts file is empty: {self.scripts_path}"
            logging.warning(msg)
            raise ValueError(msg)

        scripts = [
            line.strip()
            for line in self.scripts_text.splitlines()
            if line.strip()
        ]
        return [s for s in scripts if not script_used(s)] or scripts

    def _choose_script(self, message: str) -> str:
        options = self._available_scripts()
        if not options:
            msg = "No scripts available"
            logging.warning(msg)
            raise RuntimeError(msg)
        
        # Добавляем случайность чтобы избежать повторов
        import random
        import hashlib
        
        # Используем хеш сообщения + время для псевдослучайности
        hash_seed = int(hashlib.sha256((message + str(len(self.user_messages))).encode()).hexdigest()[:8], 16)
        random.seed(hash_seed)
        
        # Выбираем случайный скрипт из топ-30% по резонансу
        scored_scripts = []
        for script in options:
            score = resonance(message, script)
            scored_scripts.append((score, script))
        
        scored_scripts.sort(reverse=True)  # По убыванию резонанса
        top_count = max(1, len(scored_scripts) // 3)  # Топ 30%
        top_scripts = scored_scripts[:top_count]
        
        # Случайный выбор из топовых
        return random.choice(top_scripts)[1]

    def respond(self, message: str) -> str:
        # Убираем медленный scan_and_train для скорости
        self.user_messages.append(message)
        total_size = sum(len(m) for m in self.user_messages)
        if total_size > 5000:
            self.trainer.train_on_text_async('\n'.join(self.user_messages))
            self.user_messages.clear()

        # Быстрый выбор скрипта без медленных операций
        try:
            script = self._choose_script(message)
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            return str(exc)
        
        # Убираем медленные метрики и логирование для скорости
        return script


if __name__ == '__main__':
    bot = Symphony()
    try:
        while True:
            user = input('> ')
            if not user:
                continue
            reply = bot.respond(user)
            print(reply)
    except KeyboardInterrupt:
        pass

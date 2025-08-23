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
        # НЕ СОЗДАЕМ TRAINER - будем использовать память MiniLE
        self.scripts_path = Path(scripts_path)
        self.scripts_text = _load_file(self.scripts_path)
        self.user_messages: List[str] = []
        self.total_processed_size = 0
        
        # Для отслеживания изменений только в нужных папках
        self._scripts_hash = self._get_file_hash(str(scripts_path))
        
    def _get_file_hash(self, filepath: str) -> str:
        """Получить SHA256 хэш файла."""
        import hashlib
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except:
            return ""

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
        # ИСПОЛЬЗУЕМ ПРОСТОЙ КЭШ ВМЕСТО SQLite для избежания блокировок
        if not hasattr(self, '_used_scripts'):
            self._used_scripts = set()
        
        # Фильтруем использованные скрипты из памяти
        available = [s for s in scripts if s not in self._used_scripts]
        return available or scripts  # Если все использованы, возвращаем все

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
        
        # БЫСТРЫЙ выбор - берем случайный скрипт без медленного resonance
        chosen_script = random.choice(options)
        
        # Отмечаем скрипт как использованный в памяти
        if not hasattr(self, '_used_scripts'):
            self._used_scripts = set()
        self._used_scripts.add(chosen_script)
        
        return chosen_script

    def respond(self, message: str) -> str:
        # Проверяем изменения в скриптах по SHA256
        current_hash = self._get_file_hash(str(self.scripts_path))
        if current_hash != self._scripts_hash:
            self.scripts_text = _load_file(self.scripts_path)
            self._scripts_hash = current_hash
            logging.info("🔄 Scripts updated, reloaded")
        
        # НЕ ОБУЧАЕМСЯ - используем память MiniLE
        # Просто считаем размер для логики (но не обучаемся)
        self.user_messages.append(message)
        if len(self.user_messages) > 50:  # Ограничиваем память
            self.user_messages = self.user_messages[-25:]

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

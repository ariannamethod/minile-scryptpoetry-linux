import random
import importlib
import logging
from json import dump

from typing import Any
from .config import is_enabled
from .metrics import calculate_entropy, calculate_affinity

_mini_le: Any = None
MODEL_FILE: str = ""
LOG_FILE: str = ""
event_count = 0


def _load_refs():
    global _mini_le, MODEL_FILE, LOG_FILE
    if _mini_le is None:
        _mini_le = importlib.import_module("arianna_core.mini_le")
        MODEL_FILE = _mini_le.MODEL_FILE
        LOG_FILE = _mini_le.LOG_FILE
    assert _mini_le is not None


def trigger_pain(output: str, max_ent: float = 8.0) -> float:
    """Calculate pain score and mutate the model when it is high."""
    if not is_enabled("pain"):
        logging.info("[pain] feature disabled, skipping")
        return 0.0
    _load_refs()
    aff = calculate_affinity(output)
    ent = calculate_entropy(output)
    score = (1 - aff) * (max_ent - ent)
    if score > 0.5:
        model = _mini_le.load_model()
        if model:
            try:
                m = model['model'] if 'model' in model else model
                for ctx in m:
                    for ch, v in m[ctx].items():
                        m[ctx][ch] = max(1, int(v * random.uniform(0.8, 1.2)))
                with open(_mini_le.MODEL_FILE, 'w', encoding='utf-8') as f:
                    dump(model, f)
            except OSError as exc:
                logging.error("[pain] failed to update model: %s", exc)
        logging.info("Pain event: score %.2f, mutated.", score)
        global event_count
        event_count += 1
    return score


def check_once() -> None:
    """Run a single pain check if the feature is enabled."""
    if not is_enabled("pain"):
        logging.info("[pain] feature disabled, skipping")
        return
    _load_refs()
    model = _mini_le.load_model()
    if model:
        out = _mini_le.generate(model, length=20)
        trigger_pain(out)


if __name__ == '__main__':
    test_output = 'resonance echo thunder love' * 5
    trigger_pain(test_output)

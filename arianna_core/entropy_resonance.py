import copy
import json
import os
from datetime import datetime
import logging
from typing import Tuple

from . import mini_le
from .config import is_enabled
from .metrics import calculate_entropy

LOG_FILE = os.path.join(os.path.dirname(__file__), "entropy.log")

def resonance_check(entropy: float, threshold: float = 4.0) -> bool:
    """Return ``True`` if ``entropy`` exceeds ``threshold``."""
    return entropy > threshold


def entropy_mutation(model: dict, sample: str) -> dict:
    """Boost model frequencies for characters present in ``sample``."""
    if not model:
        return model
    mutated = copy.deepcopy(model)
    data = mutated["model"] if "model" in mutated else mutated
    for ch in set(sample):
        for ctx in data.values():
            if ch in ctx:
                ctx[ch] += 1
    return mutated


def entropy_resonance_mutate(model: dict) -> Tuple[dict, float, bool]:
    """Mutate ``model`` based on entropy of a generated sample."""
    sample = mini_le.generate(model, length=100)
    ent = calculate_entropy(sample)
    mutated = model
    changed = False
    if resonance_check(ent):
        mutated = entropy_mutation(model, sample)
        changed = mutated != model
    mini_le.rotate_log(LOG_FILE, mini_le.LOG_MAX_BYTES)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"{datetime.utcnow().isoformat()} entropy={ent:.2f} "
            f"changed={changed}\n"
        )
    return mutated, ent, changed


def run_once() -> None:
    """Perform an entropy resonance cycle once if the feature is enabled."""
    if not is_enabled("entropy"):
        logging.info("[entropy] feature disabled, skipping")
        return
    model = mini_le.load_model() or {}
    mutated, ent, changed = entropy_resonance_mutate(model)
    mini_le.last_entropy = ent
    if changed:
        with open(mini_le.MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(mutated, f)

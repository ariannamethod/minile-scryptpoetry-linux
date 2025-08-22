import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skryptmetrics import (  # noqa: E402
    entropy,
    perplexity,
    resonance,
    token_charge,
)


def test_entropy_and_perplexity():
    text = "aaab"
    h = entropy(text)
    assert math.isclose(h, 0.8112781244591328, rel_tol=1e-9)
    assert math.isclose(perplexity(text), 2 ** h, rel_tol=1e-9)
    assert entropy("") == 0.0


def test_resonance_and_token_charge():
    a = "hello world"
    b = "hello there"
    assert math.isclose(resonance(a, b), 1 / 3, rel_tol=1e-9)
    assert token_charge("one two three") == 3

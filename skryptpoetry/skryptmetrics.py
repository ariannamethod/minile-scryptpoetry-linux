import math
from collections import Counter

def entropy(text: str) -> float:
    """Compute Shannon entropy of text based on character distribution."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((cnt / total) * math.log2(cnt / total) for cnt in counts.values())

def perplexity(text: str) -> float:
    """Simple perplexity approximation derived from entropy."""
    h = entropy(text)
    return 2 ** h

def resonance(a: str, b: str) -> float:
    """Return Jaccard similarity between token sets of a and b."""
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)

def token_charge(text: str) -> int:
    """Simple token count representing 'charge'."""
    return len(text.split())

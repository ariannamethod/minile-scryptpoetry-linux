import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from model import GPT, GPTConfig  # noqa: E402


def test_gpt_forward_shape_cpu():
    """Ensure a tiny GPT runs a forward pass on CPU."""

    config = GPTConfig(
        block_size=4, vocab_size=10, n_layer=1, n_head=1, n_embd=8
    )
    model = GPT(config).to("cpu")

    batch_size = 2
    x = torch.randint(
        0, config.vocab_size, (batch_size, config.block_size), device="cpu"
    )
    with torch.no_grad():
        logits, _ = model(x)

    assert logits.shape == (batch_size, config.block_size, config.vocab_size)
    assert logits.device.type == "cpu"

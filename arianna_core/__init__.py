import importlib
from typing import Any

from .config import settings
from .logging_config import setup_logging

setup_logging()

mini_le: Any = importlib.import_module("arianna_core.mini_le")
server = importlib.import_module("arianna_core.server")
evolution_steps = importlib.import_module("arianna_core.evolution_steps")
bio = importlib.import_module("arianna_core.bio")
state = importlib.import_module("arianna_core.state")
rag = importlib.import_module("arianna_core.rag")
genesis = importlib.import_module("arianna_core.genesis")

__all__ = [
    "mini_le",
    "server",
    "evolution_steps",
    "settings",
    "bio",
    "state",
    "rag",
    "genesis",
]

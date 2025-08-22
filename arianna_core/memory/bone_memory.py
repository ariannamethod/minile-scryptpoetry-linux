from __future__ import annotations

from dataclasses import dataclass, field
from typing import Deque
from collections import Counter, deque


@dataclass
class BoneMemory:
    """Track recent events and compute a metabolic push coefficient."""

    limit: int
    _events: Deque[str] = field(init=False, repr=False)
    event_counts: Counter[str] = field(default_factory=Counter)
    metabolic_push: float = 0.0

    def __post_init__(self) -> None:
        self._events = deque(maxlen=self.limit)

    @property
    def events(self) -> list[str]:
        return list(self._events)

    def on_event(self, event_type: str) -> float:
        """Record an event and update ``metabolic_push``.

        The coefficient is the fraction of events of ``event_type`` in the
        current window defined by ``limit``.
        """
        if len(self._events) == self._events.maxlen:
            old_event = self._events[0]
            self.event_counts[old_event] -= 1
            if self.event_counts[old_event] == 0:
                del self.event_counts[old_event]
        self._events.append(event_type)
        self.event_counts[event_type] += 1
        self.metabolic_push = (
            self.event_counts[event_type] / len(self._events) if self._events else 0.0
        )
        return self.metabolic_push

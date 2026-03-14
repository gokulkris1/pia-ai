"""
Memory Manager — Rolling conversation history for a call session.
Keeps the last N turns to stay under token limits.
"""

import json
from collections import deque
from typing import Literal

MessageRole = Literal["user", "assistant"]


class MemoryManager:
    """
    Maintains conversation history as a rolling deque.
    Compatible with both Claude and OpenAI message formats.
    """

    def __init__(self, max_turns: int = 20):
        # max_turns * 2 because each turn has user + assistant message
        self._history: deque[dict] = deque(maxlen=max_turns * 2)

    def add(self, role: MessageRole, content: str) -> None:
        """Append a message to history."""
        self._history.append({"role": role, "content": content})

    def get_messages(self) -> list[dict]:
        """Return conversation history as a list of {role, content} dicts."""
        return list(self._history)

    def clear(self) -> None:
        """Wipe all history (used on session end)."""
        self._history.clear()

    def to_json(self) -> str:
        return json.dumps(list(self._history))

    @classmethod
    def from_json(cls, data: str, max_turns: int = 20) -> "MemoryManager":
        m = cls(max_turns=max_turns)
        for msg in json.loads(data):
            m._history.append(msg)
        return m

    def __len__(self) -> int:
        return len(self._history)

    def __repr__(self) -> str:
        return f"MemoryManager({len(self)} messages)"

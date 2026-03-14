"""
Call Session — Represents a single active call between user and PIA.
Holds the memory manager and call metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from memory.manager import MemoryManager


@dataclass
class CallSession:
    """One live call session. Created on /api/call/start, destroyed on /api/call/end."""

    session_id: str
    persona: dict[str, Any]
    started_at: datetime = field(default_factory=datetime.now)
    memory: MemoryManager = field(default_factory=MemoryManager)
    turn_count: int = 0

    def record_turn(self) -> None:
        """Increment the turn counter after each exchange."""
        self.turn_count += 1

    def duration_seconds(self) -> float:
        return (datetime.now() - self.started_at).total_seconds()

    def duration_str(self) -> str:
        """Return human-readable MM:SS duration."""
        total = int(self.duration_seconds())
        m, s = divmod(total, 60)
        return f"{m:02d}:{s:02d}"

    def __repr__(self) -> str:
        return (
            f"CallSession(id={self.session_id[:8]}…, "
            f"turns={self.turn_count}, "
            f"duration={self.duration_str()})"
        )

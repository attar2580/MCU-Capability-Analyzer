from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import Evidence


@dataclass
class BoardInfo:
    """Board-level information."""

    vendor: str
    board_name: str
    board_resources: dict[str, object] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)

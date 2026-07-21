from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import Evidence


@dataclass
class SDKExample:
    """An SDK example with its path, reasoning, and traceability."""

    path: str
    reason: str = ""
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class SDKInfo:
    """SDK information."""

    sdk_name: str
    sdk_version: str = ""
    examples: list[SDKExample] = field(default_factory=list)

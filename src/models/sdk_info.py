from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SDKExample:
    """An SDK example with its path and reasoning."""

    path: str
    reason: str = ""


@dataclass
class SDKInfo:
    """SDK information."""

    sdk_name: str
    sdk_version: str = ""
    examples: list[SDKExample] = field(default_factory=list)

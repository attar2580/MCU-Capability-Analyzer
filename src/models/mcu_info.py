from __future__ import annotations

from dataclasses import dataclass, field

from .evidence import Evidence


@dataclass
class MCUInfo:
    """MCU-level information."""

    mcu_name: str
    cpu_core: str = ""
    flash_kb: int = 0
    ram_kb: int = 0
    evidence: list[Evidence] = field(default_factory=list)

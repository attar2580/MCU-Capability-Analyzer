from __future__ import annotations

from dataclasses import dataclass, field

from .board_info import BoardInfo
from .mcu_info import MCUInfo
from .sdk_info import SDKInfo
from .capability import Capability


@dataclass
class AnalysisResult:
    """Complete internal analysis before file generation."""

    board: BoardInfo
    mcu: MCUInfo
    sdk: SDKInfo
    capabilities: list[Capability] = field(default_factory=list)

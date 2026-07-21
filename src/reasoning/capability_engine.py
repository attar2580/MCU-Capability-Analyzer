from __future__ import annotations

from ..models.board_info import BoardInfo
from ..models.mcu_info import MCUInfo
from ..models.sdk_info import SDKInfo
from ..models.capability import Capability
from .rules import ALL_RULES


class CapabilityEngine:
    """Orchestrates capability evaluation by running all registered rules."""

    def analyze(
        self, board: BoardInfo, mcu: MCUInfo, sdk: SDKInfo,
    ) -> list[Capability]:
        """Evaluate every known capability and return the results.

        Args:
            board: Collected board information.
            mcu: Collected MCU information.
            sdk: Collected SDK information.

        Returns:
            A list of ``Capability`` objects, one per registered rule.
        """
        return [rule.evaluate(board, mcu, sdk) for rule in ALL_RULES]

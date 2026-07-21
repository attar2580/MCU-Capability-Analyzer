from __future__ import annotations

from .collectors.board_collector import BoardCollector
from .collectors.mcu_collector import MCUCollector
from .collectors.sdk_collector import SDKCollector
from .models.analysis_result import AnalysisResult
from .models.sdk_info import SDKInfo
from .reasoning.capability_engine import CapabilityEngine
from .utils.doc_resolver import DocumentationResolver

_NUCLEO_MCU_MAP: dict[str, str] = {
    "NUCLEO-U083RC": "STM32U083RC",
}


def _board_to_mcu(board_name: str) -> str:
    """Derive the MCU part number from a NUCLEO board name."""
    mapped = _NUCLEO_MCU_MAP.get(board_name)
    if mapped:
        return mapped
    if board_name.startswith("NUCLEO-"):
        return "STM32" + board_name[7:]
    return board_name


class Analyzer:
    """Orchestrates the full MCU analysis pipeline.

    Usage::

        result = Analyzer().analyze(
            board_name="NUCLEO-U083RC",
            sdk_path="/path/to/STM32Cube_FW_U0",
            docs_dir="/path/to/documentation",
        )
    """

    def analyze(
        self,
        board_name: str,
        sdk_path: str | None = None,
        docs_dir: str | None = None,
    ) -> AnalysisResult:
        """Run the full analysis pipeline and return the result.

        Args:
            board_name: Board identifier (e.g. ``"NUCLEO-U083RC"``).
            sdk_path: Optional path to the STM32Cube SDK directory.
            docs_dir: Optional path to a directory of PDF documentation files.

        Returns:
            A fully populated AnalysisResult.
        """
        documents: list = (
            DocumentationResolver().resolve(docs_dir)
            if docs_dir
            else []
        )

        board = BoardCollector().collect(board_name, documents)

        mcu_name = _board_to_mcu(board_name)
        mcu = MCUCollector().collect(mcu_name, documents)

        if sdk_path:
            sdk = SDKCollector().collect(sdk_path)
        else:
            sdk = SDKInfo(sdk_name="", sdk_version="")

        capabilities = CapabilityEngine().analyze(board, mcu, sdk)

        return AnalysisResult(
            board=board,
            mcu=mcu,
            sdk=sdk,
            capabilities=capabilities,
        )

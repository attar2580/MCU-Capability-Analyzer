from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..models.analysis_result import AnalysisResult


class JsonWriter:
    """Writes an AnalysisResult as ``board_capabilities.json``.

    The output schema matches the assignment specification:
      vendor, board, mcu, cpu_core, flash_kb, ram_kb, sdk,
      board_resources, peripherals, data_sources
    """

    def build_dict(self, result: AnalysisResult) -> dict:
        """Map the internal domain model into the required JSON schema.

        Args:
            result: The analysis result to serialise.
        """
        board = result.board
        mcu = result.mcu
        sdk = result.sdk

        data_sources: list[dict] = []
        seen: set[tuple[str, str]] = set()

        def _add_source(ev: object) -> None:
            d = asdict(ev)
            key = (d["source_type"], d["document"])
            if key not in seen:
                seen.add(key)
                data_sources.append(d)

        for ev in board.evidence:
            _add_source(ev)
        for ev in mcu.evidence:
            _add_source(ev)

        peripherals: list[dict] = []
        for cap in result.capabilities:
            entry: dict = {
                "peripheral": cap.name,
                "classification": cap.classification.name,
                "evidence": [asdict(ev) for ev in cap.evidence],
            }
            if cap.sdk_examples:
                entry["sdk_examples"] = [
                    {
                        "path": ex.path,
                        "reason": ex.reason,
                        "evidence": [asdict(ev) for ev in ex.evidence],
                    }
                    for ex in cap.sdk_examples
                ]
            peripherals.append(entry)
            for ev in cap.evidence:
                _add_source(ev)
            for ex in cap.sdk_examples:
                for ev in ex.evidence:
                    _add_source(ev)

        return {
            "vendor": board.vendor,
            "board": board.board_name,
            "mcu": mcu.mcu_name,
            "cpu_core": mcu.cpu_core,
            "flash_kb": mcu.flash_kb,
            "ram_kb": mcu.ram_kb,
            "sdk": {"name": sdk.sdk_name, "version": sdk.sdk_version},
            "board_resources": dict(board.board_resources),
            "peripherals": peripherals,
            "data_sources": data_sources,
        }

    def to_string(self, result: AnalysisResult, indent: int = 2) -> str:
        """Serialize the analysis result to a JSON string.

        Args:
            result: The analysis result to serialize.
            indent: Indentation level for pretty-printing.
        """
        return json.dumps(self.build_dict(result), indent=indent)

    def write(self, result: AnalysisResult, path: str | Path) -> str:
        """Write the analysis result as JSON to *path*.

        Args:
            result: The analysis result to serialize.
            path: Destination file path.

        Returns:
            The absolute path that was written to.
        """
        path = Path(path)
        path.write_text(self.to_string(result), encoding="utf-8")
        return str(path.resolve())

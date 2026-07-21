from __future__ import annotations

from pathlib import Path

from ..models.analysis_result import AnalysisResult

_CLASSIFICATION_LABELS: dict[str, str] = {
    "SUPPORTED": "Supported",
    "SUPPORTED_MCU_NOT_BOARD": "Supported by the MCU but not available on the board",
    "REQUIRES_EXTERNAL_COMPONENT": "Requires an external component",
    "UNSUPPORTED": "Unsupported",
    "NOT_ENOUGH_VERIFIED_INFORMATION": "Not enough verified information",
}

_ASSIGNMENT_CAPABILITIES: dict[str, str] = {
    "UART": "UART logging",
    "ADC": "ADC sampling",
    "Ethernet": "Native Ethernet",
}


class ValidationWriter:
    """Answers the assignment questions directly.

    Displays:

      UART logging:
      SUPPORTED / ...

      ADC sampling:
      SUPPORTED / ...

      Native Ethernet:
      SUPPORTED / ...

    Each classification is accompanied by the supporting evidence.
    """

    def to_string(self, result: AnalysisResult) -> str:
        """Produce the assignment-answer report as plain text.

        Args:
            result: The analysis result with evaluated capabilities.
        """
        lines: list[str] = []
        lines.append("MCU Capability Analysis Report")
        lines.append("=" * 60)
        lines.append("")

        cap_by_name = {c.name: c for c in result.capabilities}

        for rule_name, display_name in _ASSIGNMENT_CAPABILITIES.items():
            lines.append(f"{display_name}:")
            cap = cap_by_name.get(rule_name)
            if cap is None:
                lines.append("  NOT EVALUATED")
                lines.append("  (no capability record found)")
                lines.append("")
                continue

            label = _CLASSIFICATION_LABELS.get(cap.classification.name, cap.classification.name)
            lines.append(f"  {label}")

            if cap.evidence:
                lines.append("  Evidence:")
                for ev in cap.evidence:
                    doc_label = ev.document if ev.document else "(unknown)"
                    lines.append(f"    - {ev.notes} (from {doc_label})")
            else:
                lines.append("  Evidence: (none collected)")

            if cap.sdk_examples:
                lines.append("  SDK examples:")
                for ex in cap.sdk_examples:
                    lines.append(f"    - {Path(ex.path).name}")
                    for ev in ex.evidence:
                        lines.append(f"      ({ev.notes})")

            lines.append("")

        lines.append("-" * 60)
        lines.append(
            f"Summary: {len(result.capabilities)} peripheral(s) evaluated"
        )
        return "\n".join(lines)

    def write(self, result: AnalysisResult, path: str | Path) -> str:
        """Write the validation / capability report to a file.

        Args:
            result: The analysis result to report on.
            path: Destination file path.

        Returns:
            The absolute path that was written to.
        """
        path = Path(path)
        path.write_text(self.to_string(result), encoding="utf-8")
        return str(path.resolve())

from __future__ import annotations

from pathlib import Path

from ..collectors.sdk_collector import SDKCollector
from ..models.analysis_result import AnalysisResult

# Map writer capability names to short scoring identifiers
_CAP_TO_SHORT: dict[str, str] = {
    "LED blinking": "LED",
    "UART communication": "UART",
    "ADC reading": "ADC",
    "Timer-based execution": "TIM",
}

# Expected category folder name for each capability (tie-breaking)
_CAP_FOLDER_NAMES: dict[str, str] = {
    "LED": "GPIO",
    "UART": "UART",
    "ADC": "ADC",
    "TIM": "TIM",
}

# Fallback search keywords when no example is found
_CAPABILITY_KEYWORDS: dict[str, list[str]] = {
    "LED blinking": ["led", "blink", "gpio"],
    "UART communication": ["uart", "usart"],
    "ADC reading": ["adc"],
    "Timer-based execution": ["timer", "tim"],
}


class SdkReportWriter:
    """Generates SDK example recommendations for each required capability."""

    def to_string(self, result: AnalysisResult) -> str:
        """Build a plain-text SDK recommendation report.

        For each assignment capability, the closest matching SDK example
        is recommended together with the reason for the recommendation.

        Recommendations use the deterministic scoring algorithm
        from ``SDKCollector._score_example``.
        """
        sdk = result.sdk
        board_name = result.board.board_name
        lines: list[str] = []
        lines.append("SDK Example Recommendations")
        lines.append("=" * 60)
        lines.append(f"SDK: {sdk.sdk_name or '(not detected)'}")
        lines.append(f"Version: {sdk.sdk_version or '(not detected)'}")
        lines.append(f"Board: {board_name}")
        lines.append("")

        for cap_name, keywords in _CAPABILITY_KEYWORDS.items():
            lines.append(f"--- {cap_name} ---")
            match = self._find_best_example(
                sdk.examples, keywords, board_name, cap_name,
            )
            if match:
                lines.append(f"  Recommended example: {Path(match.path).name}")
                lines.append(f"  Path: {match.path}")
                lines.append(f"  Reason: {match.reason}")
            else:
                lines.append("  No matching SDK example found.")
                lines.append(f"  Suggested search keywords: {', '.join(keywords)}")
            lines.append("")

        return "\n".join(lines)

    def write(self, result: AnalysisResult, path: str | Path) -> str:
        """Write the SDK recommendation report to a file.

        Args:
            result: The analysis result whose SDK info is used.
            path: Destination file path.

        Returns:
            The absolute path that was written to.
        """
        path = Path(path)
        path.write_text(self.to_string(result), encoding="utf-8")
        return str(path.resolve())

    @staticmethod
    def _find_best_example(
        examples: list, keywords: list[str],
        board_name: str = "", cap_name: str = "",
    ):
        """Return the highest-scoring SDK example using deterministic ranking.

        Scores are computed by ``SDKCollector._score_example()`` based on:
          1. Exact board match (+100)
          2. Same MCU family (+60)
          3. Same STM32U0 family (+40)
          4. Capability-specific folder (+20)
          5. Example name semantic match (+10)

        Ties are broken by (shorter path, exact capability folder, alphabetical).
        """
        cap_short = _CAP_TO_SHORT.get(cap_name, cap_name)
        expected_folder = _CAP_FOLDER_NAMES.get(cap_short, "").lower()

        scored: list[tuple[int, int, int, str, object]] = []

        for ex in examples:
            path = ex.path.replace("\\", "/")
            path_lower = path.lower()

            score = SDKCollector._score_example(ex, board_name, cap_short)

            # Tie-breaker 1: shorter path preferred
            path_len = len(path)

            # Tie-breaker 2: exact capability category folder preferred
            folder_bonus = 0
            if expected_folder and f"/{expected_folder}/" in path_lower:
                folder_bonus = 1

            scored.append((-score, path_len, -folder_bonus, path_lower, ex))

        if not scored:
            return None

        scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
        return scored[0][4]

"""CLI entry point for the MCU Capability Analyzer.

Usage:

    analyze --board NUCLEO-U083RC --sdk <path> --docs <path>

or:

    python -m src.main --board NUCLEO-U083RC --sdk <path> --docs <path>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import Analyzer
from .reports import JsonWriter, SdkReportWriter, ValidationWriter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MCU Capability Analyzer for STM32 NUCLEO-U083RC",
    )
    parser.add_argument(
        "--board", required=True,
        help="Board name (e.g. NUCLEO-U083RC)",
    )
    parser.add_argument(
        "--sdk",
        help="Path to the STM32Cube SDK directory",
    )
    parser.add_argument(
        "--docs",
        help="Path to a directory of PDF documentation files",
    )
    parser.add_argument(
        "--output", default="output",
        help="Output directory (default: output/)",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = Analyzer().analyze(
        board_name=args.board,
        sdk_path=args.sdk,
        docs_dir=args.docs,
    )

    paths = [
        JsonWriter().write(result, output_dir / "board_capabilities.json"),
        SdkReportWriter().write(result, output_dir / "sdk_recommendations.txt"),
        ValidationWriter().write(result, output_dir / "capability_validation.txt"),
    ]

    print(f"Analysis complete for {args.board}")
    for p in paths:
        print(f"  Generated: {p}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

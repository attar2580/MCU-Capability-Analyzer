from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

from ..models.evidence import Evidence
from ..models.sdk_info import SDKExample, SDKInfo
from . import SDKCollectorError

_TARGET_EXAMPLE_KEYWORDS: dict[str, list[str]] = {
    "UART": ["uart", "usart"],
    "ADC": ["adc"],
    "GPIO": ["gpio"],
    "TIM": ["timer", "tim"],
}

# Priority-4 folder keywords for scoring: capability → folder substrings
_P4_FOLDER_KEYWORDS: dict[str, list[str]] = {
    "UART": ["uart", "usart", "lpuart"],
    "ADC": ["adc"],
    "LED": ["gpio"],
    "TIM": ["tim"],
}

# Priority-5 example-name keywords for scoring: capability → name substring
_P5_NAME_KEYWORDS: dict[str, str] = {
    "UART": "uart",
    "ADC": "adc",
    "LED": "gpio",
    "TIM": "tim",
}


class SDKCollector:
    """Collects SDK information from a local SDK directory.

    Version 1 targets the STM32CubeU0 SDK layout:

        sdk/
          STM32Cube_FW_U0/          (or STM32CubeU0-main/)
            package.xml
            Projects/
              NUCLEO-U083RC/
                Examples/
                  UART/UART_TxRx/
                  ADC/ADC_Simple/
                  GPIO/GPIO_IOToggle/
                  TIM/TIM_Base/

    The collector auto-discovers the SDK root by searching for ``package.xml``
    (depth 1–2), reads metadata from ``package.xml``, and discovers examples
    under ``Projects/`` matching the target peripherals.
    """

    def collect(self, sdk_path: str) -> SDKInfo:
        """Extract SDK information by scanning the SDK directory.

        Args:
            sdk_path: Path to the SDK directory (may contain a subdirectory
                that is the actual package root).

        Returns:
            A populated SDKInfo instance.

        Raises:
            SDKCollectorError: If the SDK directory is inaccessible or no
                package root can be found.
        """
        if not os.path.isdir(sdk_path):
            raise SDKCollectorError(f"SDK directory not found: {sdk_path}")

        evidence_list: list[Evidence] = []
        root = self._discover_root(sdk_path, evidence_list)

        sdk_name = self._read_sdk_name(root, evidence_list)
        sdk_version = self._read_sdk_version(root, evidence_list)
        examples = self._find_examples(root, evidence_list)

        return SDKInfo(
            sdk_name=sdk_name,
            sdk_version=sdk_version,
            examples=examples,
        )

    # ------------------------------------------------------------------
    # SDK root discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _discover_root(
        raw_path: str, evidence_list: list[Evidence],
    ) -> str:
        """Locate the directory containing ``package.xml``.

        Checks *raw_path* first, then immediate subdirectories (depth 1),
        then one more level (depth 2).
        """
        if os.path.isfile(os.path.join(raw_path, "package.xml")):
            evidence_list.append(Evidence(
                source_type="SDK Root",
                document=raw_path,
                notes="SDK root detected at supplied path",
            ))
            return raw_path

        # Depth 1
        try:
            entries = sorted(os.listdir(raw_path))
        except OSError as exc:
            raise SDKCollectorError(
                f"Cannot list SDK directory: {raw_path} — {exc}",
            ) from exc

        for entry in entries:
            candidate = os.path.join(raw_path, entry)
            if not os.path.isdir(candidate):
                continue
            if os.path.isfile(os.path.join(candidate, "package.xml")):
                evidence_list.append(Evidence(
                    source_type="SDK Root",
                    document=candidate,
                    notes=f"SDK root discovered at depth 1: {entry}",
                ))
                return candidate

        # Depth 2
        for entry in entries:
            candidate = os.path.join(raw_path, entry)
            if not os.path.isdir(candidate):
                continue
            try:
                sub_entries = sorted(os.listdir(candidate))
            except OSError:
                continue
            for sub in sub_entries:
                candidate2 = os.path.join(candidate, sub)
                if not os.path.isdir(candidate2):
                    continue
                if os.path.isfile(os.path.join(candidate2, "package.xml")):
                    evidence_list.append(Evidence(
                        source_type="SDK Root",
                        document=candidate2,
                        notes=f"SDK root discovered at depth 2: {entry}/{sub}",
                    ))
                    return candidate2

        raise SDKCollectorError(
            f"No STM32Cube firmware package found under {raw_path}. "
            "Expected a directory with package.xml.",
        )

    # ------------------------------------------------------------------
    # Metadata: package.xml
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_package_xml(root: str) -> tuple[str, str] | None:
        """Parse ``package.xml`` and return ``(name, version)`` or ``None``.

        Expects the STM32Cube format::

            <PackDescription Release="FW.U0.1.0.0" .../>
        """
        path = os.path.join(root, "package.xml")
        if not os.path.isfile(path):
            return None
        try:
            tree = ET.parse(path)
        except (ET.ParseError, OSError):
            return None

        pd = tree.find(".//PackDescription")
        if pd is None:
            return None

        release = (pd.get("Release") or "").strip()
        if not release:
            return None

        # Format: FW.<SERIES>.<MAJOR>.<MINOR>.<PATCH>  e.g. FW.U0.1.0.0
        m = re.match(r"FW\.([A-Za-z0-9]+)\.(.+)", release, re.IGNORECASE)
        if not m:
            return None
        series = m.group(1)
        version = m.group(2)
        name = f"STM32Cube_FW_{series}"
        return name, version

    @staticmethod
    def _parse_release_notes(root: str) -> tuple[str, str] | None:
        """Fallback: parse ``Release_Notes.html`` for name and version."""
        path = os.path.join(root, "Release_Notes.html")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                html = f.read()
        except OSError:
            return None

        name = ""
        version = ""

        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1)).strip()

        m = re.search(
            r"(?:Version|V)\s*([\d]+\.[\d]+\.[\d]+(?:\.\d+)?)",
            html, re.IGNORECASE,
        )
        if m:
            version = m.group(1)

        if name or version:
            return name or "", version or ""
        return None

    # ------------------------------------------------------------------
    # SDK name
    # ------------------------------------------------------------------

    def _read_sdk_name(
        self, sdk_path: str, evidence_list: list[Evidence],
    ) -> str:
        """Read the SDK name from package metadata or directory name.

        Priority:
          1. ``package.xml`` (STM32Cube metadata).
          2. ``Release_Notes.html`` (fallback).
          3. Directory name matching ``STM32Cube_FW_U*``.
          4. Generic metadata files (sdk_name.txt, sdk.info, README.txt).
        """
        parsed = self._parse_package_xml(sdk_path)
        if parsed:
            name, _ = parsed
            if name:
                evidence_list.append(Evidence(
                    source_type="SDK Metadata",
                    document="package.xml",
                    notes=f"SDK name read from package.xml: {name}",
                ))
                return name

        html = self._parse_release_notes(sdk_path)
        if html:
            name, _ = html
            if name:
                evidence_list.append(Evidence(
                    source_type="SDK Metadata",
                    document="Release_Notes.html",
                    notes=f"SDK name read from Release_Notes.html: {name}",
                ))
                return name

        basename = os.path.basename(sdk_path)
        m = re.match(r"(STM32Cube[_\s]FW[_\s]U\d)", basename, re.IGNORECASE)
        if m:
            name = m.group(1)
            evidence_list.append(Evidence(
                source_type="SDK Directory",
                document=sdk_path,
                notes="SDK name from directory name matching STM32Cube_FW_U pattern",
            ))
            return name

        candidates = ["sdk_name.txt", "sdk.info", "README.txt"]
        for filename in candidates:
            path = os.path.join(sdk_path, filename)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    name = f.readline().strip()
                if name:
                    evidence_list.append(Evidence(
                        source_type="SDK Metadata",
                        document=filename,
                        notes=f"SDK name read from {filename}",
                    ))
                    return name
            except OSError:
                continue
        return ""

    # ------------------------------------------------------------------
    # SDK version
    # ------------------------------------------------------------------

    def _read_sdk_version(
        self, sdk_path: str, evidence_list: list[Evidence],
    ) -> str:
        """Read the SDK version from package metadata or version file.

        Priority:
          1. ``package.xml`` (STM32Cube metadata).
          2. ``Release_Notes.html`` (fallback).
          3. Common version files (fw_version.txt, version.txt, VERSION, etc.).
        """
        parsed = self._parse_package_xml(sdk_path)
        if parsed:
            _, version = parsed
            if version:
                evidence_list.append(Evidence(
                    source_type="SDK Metadata",
                    document="package.xml",
                    notes=f"SDK version read from package.xml: {version}",
                ))
                return version

        html = self._parse_release_notes(sdk_path)
        if html:
            _, version = html
            if version:
                evidence_list.append(Evidence(
                    source_type="SDK Metadata",
                    document="Release_Notes.html",
                    notes=f"SDK version read from Release_Notes.html: {version}",
                ))
                return version

        candidates = ["sdk_version.txt", "version.txt", "VERSION", "fw_version.txt"]
        for filename in candidates:
            path = os.path.join(sdk_path, filename)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    version = f.read().strip()
                if version:
                    evidence_list.append(Evidence(
                        source_type="SDK Version File",
                        document=filename,
                        notes=f"SDK version read from {filename}",
                    ))
                    return version
            except OSError:
                continue
        return ""

    # ------------------------------------------------------------------
    # Example discovery
    # ------------------------------------------------------------------

    def _find_examples(
        self, sdk_path: str, evidence_list: list[Evidence],
    ) -> list[SDKExample]:
        """Scan SDK example directories and return SDKExample objects.

        Searches under ``Projects/<board>/Examples/`` for target peripheral
        categories (UART, ADC, GPIO, TIM), then collects actual example
        directories one level deeper. Falls back to a flat scan of
        ``Examples/`` subdirectories for non-STM32Cube layouts.
        """
        examples: list[SDKExample] = []

        projects_path = os.path.join(sdk_path, "Projects")
        if os.path.isdir(projects_path):
            self._discover_examples_projects(projects_path, examples, evidence_list)

        # Generic fallback: examples/
        examples_path = os.path.join(sdk_path, "examples")
        if os.path.isdir(examples_path):
            self._collect_examples_from_dir(examples_path, examples, evidence_list)

        if not examples:
            evidence_list.append(Evidence(
                source_type="SDK Examples Directory",
                document=sdk_path,
                notes="No example subdirectories found",
            ))

        return examples

    @staticmethod
    def _discover_examples_projects(
        projects_path: str,
        examples: list[SDKExample],
        evidence_list: list[Evidence],
    ) -> None:
        """Walk ``Projects/<board>/Examples/<category>/<example>/``.

        Only examples whose category (or example name) matches a target
        peripheral are collected.
        """
        try:
            board_dirs = sorted(os.listdir(projects_path))
        except OSError as exc:
            evidence_list.append(Evidence(
                source_type="SDK Projects Directory",
                document=projects_path,
                notes=f"Failed to list Projects directory: {exc}",
            ))
            return

        for board_dir in board_dirs:
            examples_dir = os.path.join(projects_path, board_dir, "Examples")
            if not os.path.isdir(examples_dir):
                continue
            try:
                categories = sorted(os.listdir(examples_dir))
            except OSError:
                continue
            for category in categories:
                category_path = os.path.join(examples_dir, category)
                if not os.path.isdir(category_path):
                    continue
                category_lower = category.lower()
                matching_target = None
                for target, keywords in _TARGET_EXAMPLE_KEYWORDS.items():
                    if any(kw in category_lower for kw in keywords):
                        matching_target = target
                        break
                if matching_target is None:
                    continue

                try:
                    example_names = sorted(os.listdir(category_path))
                except OSError:
                    continue
                for example_name in example_names:
                    example_full = os.path.join(category_path, example_name)
                    if not os.path.isdir(example_full):
                        continue
                    reason = SDKCollector._make_example_reason(
                        example_name, matching_target,
                    )
                    examples.append(SDKExample(
                        path=example_full,
                        reason=reason,
                        evidence=[
                            Evidence(
                                source_type="SDK Examples Directory",
                                document=example_full,
                                notes=f"Found example: {example_name}",
                            ),
                        ],
                    ))

    @staticmethod
    def _make_example_reason(example_name: str, target: str) -> str:
        """Generate a human-readable reason for an SDK example."""
        name_lower = example_name.lower()
        if target == "UART":
            return "UART communication example"
        if target == "ADC":
            if "simple" in name_lower:
                return "Single-channel ADC conversion example"
            return "ADC conversion example"
        if target == "GPIO":
            if "toggle" in name_lower or "i o" in name_lower or "io" in name_lower:
                return "GPIO I/O toggle example (LED blinking)"
            return "GPIO example (LED toggling)"
        if target == "TIM":
            if "base" in name_lower:
                return "Timer base example (timer-based execution)"
            if "pwm" in name_lower:
                return "Timer PWM example"
            return "Timer-based execution example"
        return ""

    @staticmethod
    def _collect_examples_from_dir(
        directory: str,
        examples: list[SDKExample],
        evidence_list: list[Evidence],
    ) -> None:
        """Helper to enumerate immediate subdirectories as examples."""
        try:
            entries = sorted(os.listdir(directory))
        except OSError as exc:
            evidence_list.append(Evidence(
                source_type="SDK Examples Directory",
                document=directory,
                notes=f"Failed to list directory: {exc}",
            ))
            return
        for entry in entries:
            entry_full = os.path.join(directory, entry)
            if not os.path.isdir(entry_full):
                continue
            reason = SDKCollector._make_example_reason(entry, "")
            examples.append(SDKExample(
                path=entry_full,
                reason=reason,
                evidence=[
                    Evidence(
                        source_type="SDK Examples Directory",
                        document=entry_full,
                        notes=f"Found example: {entry}",
                    ),
                ],
            ))

    # ------------------------------------------------------------------
    # Example ranking
    # ------------------------------------------------------------------

    @staticmethod
    def _score_example(
        example: SDKExample,
        board_name: str,
        capability: str,
    ) -> int:
        """Score an SDK example against a target board and capability.

        Higher score = better match.  Priorities (highest → lowest):

          1. (+100) Board exactly matches ``Projects/<board_name>/``.
          2. (+60)  Same MCU family — path contains ``STM32U083``.
          3. (+40)  Same STM32U0 family — board directory under Projects/ contains ``U0``.
          4. (+20)  Capability-specific category folder match.
          5. (+10)  Example directory name contains the capability keyword.

        Scores are additive.
        """
        path = example.path.replace("\\", "/")
        path_lower = path.lower()
        board_lower = board_name.lower()

        score = 0

        # Priority 1: Board exactly matches the requested board (+100)
        if f"projects/{board_lower}/" in path_lower:
            score += 100

        # Priority 2: Same MCU family (STM32U083) (+60)
        if "stm32u083" in path_lower:
            score += 60

        # Priority 3: Same STM32U0 family (+40)
        m = re.search(r"/projects/([^/]+)/", path_lower)
        if m and "u0" in m.group(1):
            score += 40

        # Priority 4: Capability-specific category folder (+20)
        m = re.search(r"/examples/([^/]+)/", path_lower)
        if m:
            folder = m.group(1)
            for kw in _P4_FOLDER_KEYWORDS.get(capability, []):
                if kw in folder:
                    score += 20
                    break

        # Priority 5: Example name semantic match (+10)
        example_name = os.path.basename(path).lower()
        p5_kw = _P5_NAME_KEYWORDS.get(capability, "")
        if p5_kw and p5_kw in example_name:
            score += 10

        return score

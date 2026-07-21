from __future__ import annotations

import re

from ..models.evidence import Evidence
from ..models.mcu_info import MCUInfo
from ..utils.documentation import Documentation
from .base_collector import BaseCollector


class MCUCollector(BaseCollector):
    """Collects MCU-level information from datasheets and reference manuals.

    Version 1 targets STM32 NUCLEO-U083RC (Arm Cortex-M0+). Only Cortex-M
    CPU core patterns are recognised; RISC-V, MIPS and ARM-A are out of scope.
    """

    def collect(self, mcu_name: str, documents: list[Documentation]) -> MCUInfo:
        """Extract MCU information from the provided documents.

        Args:
            mcu_name: Name of the MCU.
            documents: Resolved documentation for the MCU.

        Returns:
            A populated MCUInfo instance.
        """
        evidence_list: list[Evidence] = []
        cpu_core = ""
        flash_kb = 0
        ram_kb = 0

        if not documents:
            evidence_list.append(Evidence(
                source_type="MCUCollector",
                document="N/A",
                notes="No documents provided for MCU: " + mcu_name,
            ))
            return MCUInfo(
                mcu_name=mcu_name,
                cpu_core=cpu_core,
                flash_kb=flash_kb,
                ram_kb=ram_kb,
                evidence=evidence_list,
            )

        for doc, text in self._iter_texts(documents, evidence_list):
            extracted_cpu = self._extract_cpu_core(text, doc)
            if extracted_cpu:
                cpu_core = extracted_cpu
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes=f"CPU core extracted from {doc.title}: {cpu_core}",
                ))

            # Peripheral presence check for classification accuracy
            self._check_peripheral_presence(text, doc, evidence_list)

            extracted_flash = self._extract_flash_kb(text, doc)
            if extracted_flash:
                flash_kb = extracted_flash
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes=f"Flash size extracted from {doc.title}: {flash_kb} KB",
                ))

            extracted_ram = self._extract_ram_kb(text, doc)
            if extracted_ram:
                ram_kb = extracted_ram
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes=f"RAM size extracted from {doc.title}: {ram_kb} KB",
                ))

        return MCUInfo(
            mcu_name=mcu_name,
            cpu_core=cpu_core,
            flash_kb=flash_kb,
            ram_kb=ram_kb,
            evidence=evidence_list,
        )

    @staticmethod
    def _extract_cpu_core(text: str, doc: Documentation) -> str:
        """Extract CPU core type from document text.

        Handles real STM32U0 datasheet formats::

            Arm® Cortex®-M0+ 32-bit RISC core
            Arm® Cortex®‑M0+ core            (U+2011 non-breaking hyphen)
            ARM Cortex-M0+ CPU
        """
        head = text[:6000]
        patterns = [
            # Arm ... Cortex ... M0+ with any non-word separators (® spaces, hyphens,
            # non-breaking hyphens U+2011, etc.)
            r"Arm\W*Cortex\W*M([0-9]+(?:\+)?)",
            # ARM Cortex-M0+ (common abbreviation)
            r"ARM\s*Cortex[-\s]M([0-9]+(?:\+)?)",
            # Plain Cortex-M0+
            r"Cortex[-\s]M([0-9]+(?:\+)?)",
        ]
        for p in patterns:
            m = re.search(p, head, re.IGNORECASE)
            if m:
                raw = m.group(0)
                normalised = re.sub(
                    r"\s+", " ", raw.strip(),
                ).strip()
                # Normalise trademark symbols and spacing
                normalised = normalised.replace("\u00ae", "").strip()
                # Normalise non-breaking hyphen to regular hyphen
                normalised = normalised.replace("\u2011", "-").strip()
                return normalised
        return ""

    @staticmethod
    def _extract_flash_kb(text: str, doc: Documentation) -> int:
        """Extract flash size in kilobytes from document text."""
        return MCUCollector._extract_size(text, "flash")

    @staticmethod
    def _extract_ram_kb(text: str, doc: Documentation) -> int:
        """Extract RAM size in kilobytes from document text."""
        return MCUCollector._extract_size(text, r"(?:s)?ram")

    @staticmethod
    def _extract_size(text: str, kind: str) -> int:
        """Extract a memory size in KB from text. Handles KB and MB units.

        Supports real STM32U0 datasheet formats::

            256 Kbytes of Flash memory
            256-Kbyte flash memory
            40 Kbytes of SRAM
            40-Kbyte SRAM
            1 MB Flash
        """
        # KB pattern: flexible unit and trailing text after kind keyword
        pat_kb = re.compile(
            rf"(?i)(\d+)\s*[-\u2011]?\s*"
            rf"(?:K(?:B|Byte|bytes?))\s*"
            rf"(?:of\s+)?"
            rf"(?:{kind})"
        )
        pat_kb_alt = re.compile(
            rf"(?i)(\d+)\s*[-\u2011]?\s*K\s+(?:of\s+)?(?:{kind})"
        )
        pat_mb = re.compile(
            rf"(?i)(\d+(?:\.\d+)?)\s*MB\s*(?:of\s+)?(?:{kind})",
        )

        m = pat_mb.search(text)
        if m:
            value = float(m.group(1))
            return int(value * 1024)

        m = pat_kb.search(text)
        if m:
            return int(m.group(1))

        m = pat_kb_alt.search(text)
        if m:
            return int(m.group(1))

        return 0

    @staticmethod
    def _check_peripheral_presence(
        text: str, doc: Documentation, evidence_list: list[Evidence],
    ) -> None:
        """Check which key peripherals are mentioned in the document and add evidence.

        This provides documentation traceability for capability classification
        (e.g. confirming Ethernet is not present in the official feature list).

        Negated mentions (e.g. "No Ethernet") are treated as absent.
        """
        head = text[:5000]
        lower = head.lower()
        doc_ref = doc.title or doc.source_path

        expected_peripherals = [
            ("UART", ["uart", "usart"]),
            ("ADC", ["adc"]),
            ("TIM", ["timer", "tim"]),
            ("Ethernet", ["eth", "ethernet"]),
        ]

        for name, keywords in expected_peripherals:
            found = any(kw in lower for kw in keywords)
            # Check for negation patterns: "no <keyword>", "not <keyword>"
            negated = any(
                rf"\bno\s+{kw}\b" in lower or rf"\bnot\s+{kw}\b" in lower
                for kw in keywords
            )
            if found and not negated:
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc_ref,
                    notes=f"Peripheral confirmed in {doc_ref}: {name}",
                ))
            else:
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc_ref,
                    notes=f"Peripheral not mentioned in {doc_ref}: {name}",
                ))

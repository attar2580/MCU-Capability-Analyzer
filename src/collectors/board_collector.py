from __future__ import annotations

import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..models.board_info import BoardInfo
from ..models.evidence import Evidence
from ..utils.documentation import Documentation
from .base_collector import BaseCollector


class BoardCollector(BaseCollector):
    """Collects board-level information from official documentation.

    Version 1 targets STM32 NUCLEO-U083RC and the STM32CubeU0 ecosystem.
    The architecture is extensible, but support for additional MCU families
    is intentionally out of scope.
    """

    def collect(self, board_name: str, documents: list[Documentation]) -> BoardInfo:
        """Extract board information from the provided documents.

        Args:
            board_name: Name of the board.
            documents: Resolved documentation for the board.

        Returns:
            A populated BoardInfo instance.
        """
        evidence_list: list[Evidence] = []
        vendor = ""
        board_resources: dict[str, object] = {}

        if not documents:
            evidence_list.append(Evidence(
                source_type="BoardCollector",
                document="N/A",
                notes="No documents provided for board: " + board_name,
            ))
            return BoardInfo(
                vendor=vendor,
                board_name=board_name,
                board_resources=board_resources,
                evidence=evidence_list,
            )

        for doc, text in self._iter_texts(documents, evidence_list):
            extracted_vendor = self._extract_vendor(text, doc)
            if extracted_vendor:
                vendor = extracted_vendor
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes=f"Vendor extracted from {doc.title}: {extracted_vendor}",
                ))

            extracted_resources = self._extract_board_resources(text, doc)
            if extracted_resources:
                resource_keys = ", ".join(sorted(extracted_resources.keys()))
                board_resources = self._merge_resources(
                    board_resources, extracted_resources,
                )
                evidence_list.append(Evidence(
                    source_type=doc.document_type,
                    document=doc.title or doc.source_path,
                    notes=f"Board resources extracted from {doc.title}: {resource_keys}",
                ))

        return BoardInfo(
            vendor=vendor,
            board_name=board_name,
            board_resources=board_resources,
            evidence=evidence_list,
        )

    def _extract_vendor(self, text: str, doc: Documentation) -> str:
        """Extract STMicroelectronics as vendor from PDF metadata or text.

        Version 1 targets STM32 NUCLEO-U083RC (STMicroelectronics only).
        """
        vendor = self._vendor_from_metadata(doc)
        if vendor:
            return vendor
        return self._vendor_from_text(text)

    @staticmethod
    def _vendor_from_metadata(doc: Documentation) -> str:
        """Check PDF metadata for STMicroelectronics identity."""
        try:
            reader = PdfReader(doc.source_path)
            meta = reader.metadata
            if meta:
                for field in ("/Producer", "/Author"):
                    value = meta.get(field, "")
                    if value and "stmicroelectronics" in value.lower():
                        return "STMicroelectronics"
        except (FileNotFoundError, PermissionError, PdfReadError):
            pass
        return ""

    @staticmethod
    def _vendor_from_text(text: str) -> str:
        """Search document text for STMicroelectronics identity."""
        head = text[:3000]

        if "stmicroelectronics" in head.lower():
            return "STMicroelectronics"

        if re.search(r"www\.st\.com", head, re.IGNORECASE):
            return "STMicroelectronics"

        return ""

    PIN_RE = re.compile(r"\bP[A-H]\d{1,2}\b")

    def _extract_board_resources(
        self, text: str, doc: Documentation,
    ) -> dict[str, object]:
        """Extract board resources (LED, UART, ADC, Ethernet) from text."""
        resources: dict[str, object] = {}
        lines = text.splitlines()

        led = self._extract_led(lines)
        if led:
            resources["led"] = led

        uart = self._extract_debug_uart(lines)
        if uart:
            resources["debug_uart"] = uart

        adc = self._extract_adc(lines)
        if adc:
            resources["adc"] = adc

        eth = self._extract_ethernet(lines)
        if eth:
            resources["ethernet"] = eth

        return resources

    @staticmethod
    def _extract_led(lines: list[str]) -> dict[str, object] | None:
        """Extract LED resource info from document lines."""
        for line in lines:
            if not re.search(r"\b(?:LED|LD\d*)\b", line, re.IGNORECASE):
                continue
            pins = BoardCollector.PIN_RE.findall(line)
            if not pins:
                continue
            # Determine label
            label_m = re.search(r"(?:LD\d+|LED\d+)", line, re.IGNORECASE)
            label = label_m.group(0) if label_m else ""
            color_m = re.search(r"\b(red|green|blue|yellow|orange|white)\b", line, re.IGNORECASE)
            entry: dict[str, object] = {"pin": pins[0]}
            if label:
                entry["label"] = label
            if color_m:
                entry["color"] = color_m.group(0).lower()
            return entry
        return None

    @staticmethod
    def _extract_debug_uart(lines: list[str]) -> dict[str, object] | None:
        """Extract debug UART info from document lines."""
        uart_instance: str | None = None
        tx_pin: str | None = None
        rx_pin: str | None = None

        for line in lines:
            if not re.search(r"\b(?:UART\d*|USART\d*|VCP|virtual\s*com)", line, re.IGNORECASE):
                continue
            pins = BoardCollector.PIN_RE.findall(line)
            if not pins:
                continue

            if not uart_instance:
                inst_m = re.search(r"(UART\d+|USART\d+)", line, re.IGNORECASE)
                if inst_m:
                    uart_instance = inst_m.group(0).upper()

            has_tx = bool(re.search(r"(?<![A-Za-z])TX(?![A-Za-z])", line, re.IGNORECASE))
            has_rx = bool(re.search(r"(?<![A-Za-z])RX(?![A-Za-z])", line, re.IGNORECASE))

            if has_tx and not tx_pin:
                tx_pin = pins[0]
            if has_rx and not rx_pin:
                rx_pin = pins[0] if not has_tx or len(pins) == 1 else pins[1]

            if not has_tx and not has_rx and len(pins) >= 2:
                if tx_pin is None and rx_pin is None:
                    tx_pin = pins[0]
                    rx_pin = pins[1]

        if tx_pin or rx_pin:
            result: dict[str, object] = {}
            if uart_instance:
                result["instance"] = uart_instance
            if tx_pin:
                result["tx_pin"] = tx_pin
            if rx_pin:
                result["rx_pin"] = rx_pin
            return result
        return None

    @staticmethod
    def _extract_adc(lines: list[str]) -> dict[str, object] | None:
        """Extract ADC resource info from document lines."""
        adc_instance = None
        pins: list[str] = []

        for line in lines:
            if not re.search(r"\bADC\d*", line, re.IGNORECASE):
                continue
            if adc_instance is None:
                inst_m = re.search(r"(ADC\d*)", line, re.IGNORECASE)
                if inst_m:
                    adc_instance = inst_m.group(0).upper()
            found = BoardCollector.PIN_RE.findall(line)
            pins.extend(found)

        if adc_instance or pins:
            result: dict[str, object] = {}
            if adc_instance:
                result["instance"] = adc_instance
            if pins:
                result["pins"] = pins
            return result
        return None

    @staticmethod
    def _extract_ethernet(lines: list[str]) -> dict[str, object] | None:
        """Extract Ethernet resource info from document lines."""
        for line in lines:
            if not re.search(r"\b(?:ETH\d*|ETHERNET)", line, re.IGNORECASE):
                continue
            result: dict[str, object] = {}
            interface_m = re.search(r"\b(RMII|MII|RGMII)\b", line, re.IGNORECASE)
            if interface_m:
                result["interface"] = interface_m.group(0).upper()
            else:
                result["interface"] = ""
            pins = BoardCollector.PIN_RE.findall(line)
            if pins:
                result["pins"] = pins
            return result
        return None

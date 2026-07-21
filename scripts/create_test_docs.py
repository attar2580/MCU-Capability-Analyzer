"""Create synthetic STM32 PDF documentation for end-to-end testing.

Uses realistic text matching the official STM32U083RC datasheet format.
"""

import os


def _make_pdf(text: str) -> bytes:
    """Build a minimal valid PDF with *text* as extractable content."""
    text_bytes = text.encode("latin-1")
    safe = text_bytes.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")

    stream = (
        b"BT\n"
        b"/F1 10 Tf\n"
        b"10 750 Td\n"
        b"(" + safe + b") Tj\n"
        b"ET\n"
    )
    stream_len = len(stream)

    header = b"%PDF-1.4\n"
    offset = len(header)

    chunks: list[tuple[int, bytes]] = []

    def emit(num: int, data: bytes) -> None:
        nonlocal offset
        chunks.append((offset, num, data))
        line = f"{num} 0 obj\n".encode() + data + b"\nendobj\n"
        offset += len(line)

    emit(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    emit(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    emit(3, (
        b"<< /Type /Page /Parent 2 0 R\n"
        b"   /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R\n"
        b"   /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>\n"
        b">>"
    ))
    emit(4, b"<< /Length " + str(stream_len).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    body = b""
    xref_map: dict[int, int] = {}
    for off, num, data in chunks:
        xref_map[num] = off
        body += f"{num} 0 obj\n".encode() + data + b"\nendobj\n"

    xref_offset = len(header) + len(body)
    xref = b"xref\n"
    xref += b"0 6\n"
    xref += b"0000000000 65535 f \n"
    for num in range(1, 6):
        off = xref_map.get(num, 0)
        xref += f"{off:010d} 00000 n \n".encode()

    trailer = b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
    result = header + body + xref + trailer + b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    return result


def create_test_docs(directory: str, use_registered_symbol: bool = False) -> list[str]:
    """Generate synthetic test PDFs and return their paths."""
    os.makedirs(directory, exist_ok=True)
    paths = []

    # Datasheet - uses "Arm Cortex-M0+" (without ® for Latin-1 compatibility)
    # The pdf parser handles both formats; for Latin-1 PDF we avoid the ® symbol
    ds_text = (
        "STM32U083RC\n"
        "Ultra-low-power Arm Cortex-M0+ 32-bit MCU\n"
        "256-Kbyte flash memory and 40-Kbyte SRAM\n"
        "256 Kbytes of Flash memory\n"
        "40 Kbytes of SRAM\n"
        "Peripherals:\n"
        "- 4 USARTs/LPUARTs\n"
        "- 4 I2C interfaces\n"
        "- 3 SPIs\n"
        "- 1 USB 2.0 full-speed\n"
        "- 1 12-bit ADC\n"
        "- 1 12-bit DAC\n"
        "- Advanced-control timer\n"
        "- General-purpose timers\n"
        "- Basic timers\n"
        "- Low-power timers\n"
    )
    path = os.path.join(directory, "DS_STM32U083RC.pdf")
    with open(path, "wb") as f:
        f.write(_make_pdf(ds_text))
    paths.append(path)

    # User Manual - board-level info
    um_text = (
        "www.st.com\n"
        "NUCLEO-U083RC\n"
        "LED LD3 red PC0\n"
        "USART2 TX PD5 RX PD6\n"
        "ADC1\n"
    )
    path = os.path.join(directory, "UM_NUCLEO-U083RC.pdf")
    with open(path, "wb") as f:
        f.write(_make_pdf(um_text))
    paths.append(path)

    return paths


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    paths = create_test_docs(target)
    for p in paths:
        print(p)

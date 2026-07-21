from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Documentation:
    """A resolved official document for a board or MCU."""

    source_path: str
    document_type: str
    title: str = ""
    revision: str = ""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Evidence:
    """Traceability information for one extracted value."""

    source_type: str
    document: str
    section: str = ""
    page: str = ""
    notes: str = ""

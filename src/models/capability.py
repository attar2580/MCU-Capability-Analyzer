from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from .evidence import Evidence
from .sdk_info import SDKExample


class Classification(Enum):
    """Classification of an MCU or board capability."""

    SUPPORTED = auto()
    SUPPORTED_MCU_NOT_BOARD = auto()
    REQUIRES_EXTERNAL_COMPONENT = auto()
    UNSUPPORTED = auto()
    NOT_ENOUGH_VERIFIED_INFORMATION = auto()


@dataclass
class Capability:
    """One capability of the MCU or board."""

    name: str
    classification: Classification
    evidence: list[Evidence] = field(default_factory=list)
    sdk_examples: list[SDKExample] = field(default_factory=list)

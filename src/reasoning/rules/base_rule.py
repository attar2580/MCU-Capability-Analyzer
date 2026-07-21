from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ...models.capability import Capability, Classification
from ...models.evidence import Evidence
from ...models.sdk_info import SDKExample


@dataclass
class EvaluationResult:
    """Internal result produced by a rule's evaluation logic."""

    classification: Classification
    evidence: list[Evidence] = field(default_factory=list)
    sdk_examples: list[SDKExample] = field(default_factory=list)


class BaseRule(ABC):
    """Abstract base for capability evaluation rules.

    Subclasses must define ``name`` and implement ``_evaluate()``.
    The template method ``evaluate()`` wraps the result in a ``Capability``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable capability name (e.g. ``"UART"``)."""

    def evaluate(
        self, board: BoardInfo, mcu: MCUInfo, sdk: SDKInfo,
    ) -> Capability:
        """Evaluate this capability and return a fully populated ``Capability``.

        Args:
            board: Collected board information.
            mcu: Collected MCU information.
            sdk: Collected SDK information.

        Returns:
            A ``Capability`` with the determined classification and evidence.
        """
        result = self._evaluate(board, mcu, sdk)
        return Capability(
            name=self.name,
            classification=result.classification,
            evidence=result.evidence,
            sdk_examples=result.sdk_examples,
        )

    @abstractmethod
    def _evaluate(
        self, board: BoardInfo, mcu: MCUInfo, sdk: SDKInfo,
    ) -> EvaluationResult:
        """Determine the classification and gather supporting evidence.

        Subclasses must follow the deterministic check order:
            1. NOT_ENOUGH_VERIFIED_INFORMATION
            2. SUPPORTED
            3. SUPPORTED_MCU_NOT_BOARD
            4. REQUIRES_EXTERNAL_COMPONENT
            5. UNSUPPORTED
        """

    @staticmethod
    def collect_relevant_evidence(
        board: BoardInfo,
        mcu: MCUInfo,
        sdk: SDKInfo,
        keyword: str,
    ) -> list[Evidence]:
        """Collect evidence whose notes contain *keyword* from all sources.

        Args:
            board: Board information whose evidence list is searched.
            mcu: MCU information whose evidence list is searched.
            sdk: SDK information; matching examples contribute their evidence.
            keyword: Case-insensitive keyword to match against evidence notes
                and SDK example paths.

        Returns:
            A list of matching ``Evidence`` objects.
        """
        evidence: list[Evidence] = []
        keyword_lower = keyword.lower()

        for ev in board.evidence:
            if keyword_lower in ev.notes.lower():
                evidence.append(ev)

        for ev in mcu.evidence:
            if keyword_lower in ev.notes.lower():
                evidence.append(ev)

        for ex in sdk.examples:
            if keyword_lower in ex.path.lower() or keyword_lower in ex.reason.lower():
                evidence.extend(ex.evidence)

        return evidence

    @staticmethod
    def _has_board_resource(
        board: BoardInfo, *keywords: str,
    ) -> bool:
        """Check if *board.board_resources* contains any of the given keywords."""
        keys_lower = [k.lower() for k in board.board_resources]
        return any(kw.lower() in key for key in keys_lower for kw in keywords)

    @staticmethod
    def _filter_sdk_examples(
        sdk: SDKInfo, *keywords: str,
    ) -> list[SDKExample]:
        """Return SDK examples whose path or reason contains any keyword."""
        result: list[SDKExample] = []
        for ex in sdk.examples:
            if any(kw.lower() in ex.path.lower() or kw.lower() in ex.reason.lower() for kw in keywords):
                result.append(ex)
        return result


# Late imports to avoid circular dependencies at module level
from ...models.board_info import BoardInfo  # noqa: E402
from ...models.mcu_info import MCUInfo  # noqa: E402
from ...models.sdk_info import SDKInfo  # noqa: E402

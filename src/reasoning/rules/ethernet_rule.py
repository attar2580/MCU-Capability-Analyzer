from __future__ import annotations

from ...models.board_info import BoardInfo
from ...models.mcu_info import MCUInfo
from ...models.sdk_info import SDKInfo
from ...models.capability import Classification
from .base_rule import BaseRule, EvaluationResult


class EthernetRule(BaseRule):
    """Evaluates Ethernet capability based on collected information."""

    @property
    def name(self) -> str:
        return "Ethernet"

    def _evaluate(
        self, board: BoardInfo, mcu: MCUInfo, sdk: SDKInfo,
    ) -> EvaluationResult:
        has_resource = self._has_board_resource(board, "eth", "ethernet")
        examples = self._filter_sdk_examples(sdk, "eth", "ethernet")
        evidence = self.collect_relevant_evidence(board, mcu, sdk, "ethernet")

        # Check MCU-level evidence for explicit "not mentioned" determination
        mcu_confirms_unsupported = any(
            "not mentioned" in ev.notes.lower() and "ethernet" in ev.notes.lower()
            for ev in mcu.evidence
        )

        if not has_resource and not examples:
            if mcu_confirms_unsupported:
                return EvaluationResult(
                    Classification.UNSUPPORTED, evidence,
                )
            return EvaluationResult(
                Classification.NOT_ENOUGH_VERIFIED_INFORMATION, evidence,
            )

        if has_resource:
            return EvaluationResult(
                Classification.SUPPORTED, evidence, examples,
            )

        if examples:
            return EvaluationResult(
                Classification.SUPPORTED_MCU_NOT_BOARD, evidence, examples,
            )

        return EvaluationResult(
            Classification.UNSUPPORTED, evidence,
        )

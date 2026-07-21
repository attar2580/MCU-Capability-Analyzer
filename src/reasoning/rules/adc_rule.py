from __future__ import annotations

from ...models.board_info import BoardInfo
from ...models.mcu_info import MCUInfo
from ...models.sdk_info import SDKInfo
from ...models.capability import Classification
from .base_rule import BaseRule, EvaluationResult


class ADCRule(BaseRule):
    """Evaluates ADC capability based on collected information."""

    @property
    def name(self) -> str:
        return "ADC"

    def _evaluate(
        self, board: BoardInfo, mcu: MCUInfo, sdk: SDKInfo,
    ) -> EvaluationResult:
        has_resource = self._has_board_resource(board, "adc")
        examples = self._filter_sdk_examples(sdk, "adc")
        evidence = self.collect_relevant_evidence(board, mcu, sdk, "adc")

        if not has_resource and not examples:
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

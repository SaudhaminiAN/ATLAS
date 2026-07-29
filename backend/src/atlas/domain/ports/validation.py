"""Trade validation service port."""

from typing import Protocol

from atlas.domain.models.validation import ValidationContext, ValidationResult, ValidationRuleResult


class ValidationRuleProtocol(Protocol):
    """Single declarative validation rule."""

    name: str

    def evaluate(self, context: ValidationContext) -> ValidationRuleResult: ...


class TradeValidationServiceProtocol(Protocol):
    """Apply deterministic pass/fail rules to confluence output."""

    def validate(self, context: ValidationContext) -> ValidationResult: ...

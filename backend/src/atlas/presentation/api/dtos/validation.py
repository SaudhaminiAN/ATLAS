"""Validation API DTOs."""

from datetime import datetime

from pydantic import BaseModel


class ValidationRuleResultDTO(BaseModel):
    """Single validation rule outcome."""

    rule_name: str
    passed: bool
    reason: str
    enabled: bool


class ValidationResultDTO(BaseModel):
    """Trade validation snapshot."""

    symbol: str
    direction: str
    is_valid: bool
    rules: list[ValidationRuleResultDTO]
    failed_rules: list[str]
    strategy_profile_id: str
    validated_at: datetime

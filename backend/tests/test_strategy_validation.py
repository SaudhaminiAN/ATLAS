"""Strategy profile validation tests."""

from decimal import Decimal

from atlas.domain.models.enums import Direction
from atlas.domain.models.strategy import StrategyProfile
from atlas.domain.services.strategy_validation import validate_profile_config

VALID_CONFIG = {
    "min_confluence_score": 0.70,
    "enabled_directions": ["BUY", "SELL"],
    "confluence_weights": {
        "mtf_alignment": 0.25,
        "smc_structure": 0.25,
        "price_action": 0.20,
        "technical_levels": 0.15,
        "market_context": 0.15,
    },
    "active_timeframes": ["D1", "H4", "H1", "M15"],
    "allowed_sessions": ["london", "new_york", "overlap"],
    "validation_rules": {
        "mtf_alignment_minimum": True,
        "confluence_score_minimum": True,
        "no_counter_trend": True,
        "minimum_rr_potential": True,
        "news_block": True,
        "session_check": True,
        "spread_check": True,
        "volatility_check": True,
    },
}


def test_valid_config_passes() -> None:
    assert validate_profile_config(VALID_CONFIG) == []


def test_weights_must_sum_to_one() -> None:
    config = {
        **VALID_CONFIG,
        "confluence_weights": {
            "mtf_alignment": 0.5,
            "smc_structure": 0.5,
            "price_action": 0.5,
            "technical_levels": 0.0,
            "market_context": 0.0,
        },
    }
    errors = validate_profile_config(config)
    assert any("sum to 1.0" in e for e in errors)


def test_min_confluence_score_out_of_range() -> None:
    config = {**VALID_CONFIG, "min_confluence_score": 1.5}
    errors = validate_profile_config(config)
    assert any("min_confluence_score" in e for e in errors)


def test_enabled_directions_non_empty() -> None:
    config = {**VALID_CONFIG, "enabled_directions": []}
    errors = validate_profile_config(config)
    assert any("enabled_directions" in e for e in errors)


def test_wait_direction_rejected() -> None:
    config = {**VALID_CONFIG, "enabled_directions": ["WAIT"]}
    errors = validate_profile_config(config)
    assert any("WAIT" in e for e in errors)


def test_active_timeframes_minimum() -> None:
    config = {**VALID_CONFIG, "active_timeframes": ["M15"]}
    errors = validate_profile_config(config)
    assert any("active_timeframes" in e for e in errors)


def test_unknown_validation_rule_rejected() -> None:
    config = {
        **VALID_CONFIG,
        "validation_rules": {
            **VALID_CONFIG["validation_rules"],
            "made_up_rule": True,
        },
    }
    errors = validate_profile_config(config)
    assert any("unknown validation rule" in e for e in errors)


def test_all_rules_disabled_rejected() -> None:
    config = {
        **VALID_CONFIG,
        "validation_rules": {k: False for k in VALID_CONFIG["validation_rules"]},
    }
    errors = validate_profile_config(config)
    assert any("at least one validation rule" in e for e in errors)


def test_direction_filter_on_profile() -> None:
    from datetime import UTC, datetime

    profile = StrategyProfile(
        id="test",
        name="Test",
        min_confluence_score=Decimal("0.7"),
        enabled_directions=(Direction.BUY,),
        confluence_weights={"mtf_alignment": Decimal("1.0")},
        active_timeframes=(),
        allowed_sessions=(),
        validation_rule_flags={"session_check": True},
        is_active=True,
        updated_at=datetime.now(UTC),
    )
    assert profile.is_direction_enabled(Direction.BUY) is True
    assert profile.is_direction_enabled(Direction.SELL) is False
    assert profile.is_rule_enabled("session_check") is True
    assert profile.is_rule_enabled("news_block") is False

"""Strategy engine service tests."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from atlas.application.strategy.service import (
    ProfileNotFoundError,
    ProfileValidationError,
    StrategyEngineService,
)
from atlas.domain.events.base import DomainEvent
from atlas.domain.models.strategy import DEFAULT_PROFILE_ID
from atlas.infrastructure.events.in_memory_bus import InMemoryEventBus

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


def _make_model(
    profile_id: str = DEFAULT_PROFILE_ID,
    *,
    is_active: bool = True,
    config: dict | None = None,
):
    model = MagicMock()
    model.id = profile_id
    model.name = "XAUUSD Conservative"
    model.config = config or VALID_CONFIG
    model.is_active = is_active
    model.updated_at = datetime.now(UTC)
    return model


class FakeStrategyRepo:
    def __init__(self) -> None:
        self.profiles = {DEFAULT_PROFILE_ID: _make_model()}
        self.active_id = DEFAULT_PROFILE_ID

    async def list_all(self):
        return list(self.profiles.values())

    async def get_by_id(self, profile_id: str):
        return self.profiles.get(profile_id)

    async def get_active(self):
        for profile in self.profiles.values():
            if profile.is_active:
                return profile
        return None

    async def set_active(self, profile_id: str):
        if profile_id not in self.profiles:
            return None
        for profile in self.profiles.values():
            profile.is_active = profile.id == profile_id
        self.active_id = profile_id
        return self.profiles[profile_id]

    async def ensure_default_active(self):
        active = await self.get_active()
        if active:
            return active
        return await self.set_active(DEFAULT_PROFILE_ID)


class FakeProfileCache:
    def __init__(self) -> None:
        self.profile = None

    async def get_active(self):
        return self.profile

    async def set_active(self, profile):
        self.profile = profile

    async def invalidate(self):
        self.profile = None


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def strategy_setup(monkeypatch):
    bus = InMemoryEventBus()
    cache = FakeProfileCache()
    repo = FakeStrategyRepo()
    events: list[DomainEvent] = []
    bus.subscribe("strategy.profile.changed", lambda e: events.append(e))

    def session_factory():
        return FakeSession()

    monkeypatch.setattr(
        "atlas.application.strategy.service.StrategyProfileRepository",
        lambda session: repo,
    )

    service = StrategyEngineService(
        session_factory=session_factory,  # type: ignore[arg-type]
        event_bus=bus,
        profile_cache=cache,  # type: ignore[arg-type]
    )
    return service, repo, cache, events


@pytest.mark.asyncio
async def test_get_active_from_database(strategy_setup) -> None:
    service, repo, cache, _ = strategy_setup
    profile = await service.get_active()
    assert profile.id == DEFAULT_PROFILE_ID
    assert cache.profile is not None


@pytest.mark.asyncio
async def test_get_active_uses_cache(strategy_setup) -> None:
    service, _, cache, _ = strategy_setup
    first = await service.get_active()
    second = await service.get_active()
    assert second.id == first.id
    assert cache.profile is not None


@pytest.mark.asyncio
async def test_set_active_emits_event(strategy_setup) -> None:
    service, repo, _, events = strategy_setup
    alt = _make_model("xauusd_aggressive", is_active=False)
    repo.profiles["xauusd_aggressive"] = alt

    profile = await service.set_active("xauusd_aggressive")
    assert profile.id == "xauusd_aggressive"
    assert len(events) == 1
    assert events[0].event_type == "strategy.profile.changed"
    assert events[0].payload["profile_id"] == "xauusd_aggressive"


@pytest.mark.asyncio
async def test_set_active_not_found(strategy_setup) -> None:
    service, _, _, _ = strategy_setup
    with pytest.raises(ProfileNotFoundError):
        await service.set_active("missing")


@pytest.mark.asyncio
async def test_set_active_invalid_config(strategy_setup) -> None:
    service, repo, _, _ = strategy_setup
    bad = _make_model(
        "bad_profile",
        is_active=False,
        config={**VALID_CONFIG, "min_confluence_score": 2.0},
    )
    repo.profiles["bad_profile"] = bad

    with pytest.raises(ProfileValidationError) as exc:
        await service.set_active("bad_profile")
    assert any("min_confluence_score" in e for e in exc.value.errors)


@pytest.mark.asyncio
async def test_list_profiles(strategy_setup) -> None:
    service, repo, _, _ = strategy_setup
    repo.profiles["other"] = _make_model("other", is_active=False)
    profiles = await service.list_profiles()
    assert {p.id for p in profiles} == {DEFAULT_PROFILE_ID, "other"}

from datetime import datetime, timedelta, timezone

import pytest

from app.engines.priority_score import age_days, live_score, parse_ts

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
CREATED = NOW - timedelta(days=3)


def test_age_days_continuous():
    assert age_days(CREATED, NOW) == pytest.approx(3.0)
    assert age_days((NOW - timedelta(hours=12)).isoformat(), NOW) == pytest.approx(0.5)


def test_parse_ts_z_suffix():
    assert parse_ts("2026-10-03T12:00:00Z") == NOW


def test_linear_decay_formula():
    # score = max(0, base - k * age_days)
    assert live_score(10, CREATED, NOW, decay_per_day=1.0) == pytest.approx(7.0)
    assert live_score(10, NOW, NOW, decay_per_day=1.0) == pytest.approx(10.0)
    assert live_score(10, NOW - timedelta(hours=12), NOW, decay_per_day=2.0) == pytest.approx(9.0)


def test_score_floored_at_zero():
    old = NOW - timedelta(days=30)
    assert live_score(10, old, NOW, decay_per_day=1.0) == 0.0


def test_zero_decay_keeps_base():
    assert live_score(10, NOW - timedelta(days=999), NOW, decay_per_day=0.0) == pytest.approx(10.0)


def test_future_created_at_clamps_age_to_zero():
    assert live_score(10, NOW + timedelta(days=1), NOW, decay_per_day=1.0) == pytest.approx(10.0)


def test_nonpositive_base_rejected():
    with pytest.raises(ValueError):
        live_score(0, NOW, NOW, decay_per_day=1.0)
    with pytest.raises(ValueError):
        live_score(-1, NOW, NOW, decay_per_day=1.0)


def test_negative_decay_rejected():
    with pytest.raises(ValueError):
        live_score(10, NOW, NOW, decay_per_day=-0.1)

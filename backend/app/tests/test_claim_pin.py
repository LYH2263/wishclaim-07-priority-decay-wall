from datetime import datetime, timedelta, timezone
from app.modules import claim_pin
from app.modules.priority_score import live_score

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
BIRTH = NOW - timedelta(days=2)


def test_snapshot_equals_live_score_at_claim_instant():
    snap = claim_pin.snapshot(100, BIRTH, NOW, decay_per_day=10)
    assert snap["pinned_score"] == live_score(100, BIRTH, NOW, 10) == 80.0


def test_pinned_score_frozen_after_decay_param_change():
    snap = claim_pin.snapshot(100, BIRTH, NOW, decay_per_day=10)
    pinned = snap["pinned_score"]
    # 之后把衰减率改为 999：若此刻重新认领，分数完全不同；但旧钉分不动
    assert live_score(100, BIRTH, NOW, decay_per_day=999) == 0.0
    assert pinned == 80.0


def test_pinned_score_frozen_as_time_passes():
    pinned = claim_pin.snapshot(100, BIRTH, NOW, 10)["pinned_score"]
    later = NOW + timedelta(days=100)
    assert live_score(100, BIRTH, later, 10) == 0.0
    assert pinned == 80.0


def test_release_clears_pin():
    assert claim_pin.clear() == {"pinned_score": None}

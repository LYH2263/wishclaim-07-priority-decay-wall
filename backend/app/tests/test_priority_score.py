from datetime import datetime, timedelta, timezone
from app.modules.priority_score import age_days, live_score, valid_base_priority

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
BIRTH = NOW - timedelta(days=3)


def test_age_days_linear():
    assert age_days(BIRTH, NOW) == 3.0
    # 未来时间戳不计负年龄
    assert age_days(NOW + timedelta(days=1), NOW) == 0.0
    # 接受 ISO 字符串
    assert age_days(BIRTH.isoformat(), NOW) == 3.0


def test_linear_decay_formula():
    # 100 分、每天衰 10 分、过 3 天 => 70
    assert live_score(100, BIRTH, NOW, decay_per_day=10) == 70.0


def test_decay_hits_floor_zero():
    assert live_score(10, BIRTH, NOW, decay_per_day=10) == 0.0
    # 衰减率为 0 时永不掉分
    assert live_score(100, BIRTH, NOW, decay_per_day=0) == 100.0


def test_partial_day_is_linear_not_stepwise():
    # 半天就衰半天的分，阶梯衰减不会有此结果
    half_day = NOW - timedelta(hours=12)
    assert live_score(100, half_day, NOW, decay_per_day=10) == 95.0


def test_valid_base_priority():
    assert valid_base_priority(1) and valid_base_priority(0.01) and valid_base_priority("12")
    assert not valid_base_priority(0)
    assert not valid_base_priority(-1)
    assert not valid_base_priority(None)
    assert not valid_base_priority("abc")

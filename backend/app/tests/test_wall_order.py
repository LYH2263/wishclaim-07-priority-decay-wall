from datetime import datetime, timedelta, timezone
from app.modules.wall_order import effective_score, order_rows, project

NOW = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)


def row(id, status, base, created_offset_days, pinned=None):
    return {
        "id": id, "status": status,
        "base_priority": base,
        "created_at": (NOW - timedelta(days=created_offset_days)).isoformat(),
        "pinned_score": pinned,
    }


def test_open_rows_decay_with_age():
    rows = [
        row(1, "open", 100, 0),       # 新愿望 100
        row(2, "open", 100, 3),       # 老愿望 70
    ]
    out = order_rows(rows, NOW, decay_per_day=10)
    assert [r["id"] for r in out] == [1, 2]
    assert out[0]["score"] == 100.0 and out[1]["score"] == 70.0


def test_released_keeps_aging():
    # released 仍按 created_at 实时衰减，分数随时间继续掉
    r = row(3, "released", 100, 2)
    assert effective_score(r, NOW, 10) == 80.0
    assert effective_score(r, NOW + timedelta(days=1), 10) == 70.0


def test_claimed_uses_pinned_score():
    claimed = row(4, "claimed", 100, 2, pinned=80.0)
    # 无论时间推进还是调大衰减率，钉分不变
    assert effective_score(claimed, NOW + timedelta(days=30), 10) == 80.0
    assert effective_score(claimed, NOW + timedelta(days=30), 999) == 80.0


def test_pinned_outranks_new_decay_change():
    # 钉分 80 的已认领条目；把衰减率调到 999 后 open 条目归零，钉分仍在
    claimed = row(5, "claimed", 100, 2, pinned=80.0)
    fresh = row(6, "open", 100, 1)  # 1 天后在 999/天 的衰减下归零
    out = order_rows([fresh, claimed], NOW, decay_per_day=999)
    assert [r["id"] for r in out] == [5, 6]
    assert out[0]["score"] == 80.0 and out[1]["score"] == 0.0


def test_project_exposes_live_score_for_cross_check():
    # 已认领条目同时给出 live_score（继续算）与 score（钉分），详情页并列可核对
    claimed = row(7, "claimed", 100, 2, pinned=80.0)
    p = project(claimed, NOW + timedelta(days=3), 10)
    assert p["score"] == 80.0       # 钉分
    assert p["live_score"] == 50.0  # 若未认领此刻应有的分数


def test_tie_break_is_older_first_then_id():
    a = row(10, "open", 100, 1)
    b = row(11, "open", 100, 1)
    out = order_rows([b, a], NOW, 10)
    assert [r["id"] for r in out] == [10, 11]

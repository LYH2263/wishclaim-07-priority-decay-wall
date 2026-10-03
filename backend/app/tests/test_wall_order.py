from datetime import datetime, timedelta, timezone

from app.engines.wall_order import project_wall, projected_score

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
K = 1.0  # decay_per_day


def wish(wid, status, base=10.0, age_days=0.0, pinned=None, created=None):
    ts = (created or (NOW - timedelta(days=age_days))).isoformat()
    return {"id": wid, "title": f"w{wid}", "status": status,
            "base_priority": base, "created_at": ts, "pinned_score": pinned}


def test_open_uses_live_score():
    s, kind = projected_score(wish(1, "open", 10, age_days=3), NOW, K)
    assert kind == "live" and s == 7.0


def test_released_uses_live_score():
    s, kind = projected_score(wish(1, "released", 10, age_days=1), NOW, K)
    assert kind == "live" and s == 9.0


def test_claimed_uses_pinned_snapshot():
    # 钉分 7.4 即使距创建已 30 天（实时分早已封底 0）也不变。
    s, kind = projected_score(wish(1, "claimed", 10, age_days=30, pinned=7.4), NOW, K)
    assert kind == "pinned" and s == 7.4


def test_fulfilled_uses_pinned_snapshot():
    s, kind = projected_score(wish(1, "fulfilled", 10, age_days=30, pinned=5.0), NOW, K)
    assert kind == "pinned" and s == 5.0


def test_pinned_unaffected_by_param_change():
    # 把衰减参数从 1.0 改成 100.0：钉分不动，实时分重排。
    w = wish(1, "claimed", 10, age_days=30, pinned=7.4)
    assert projected_score(w, NOW, 1.0)[0] == 7.4
    assert projected_score(w, NOW, 100.0)[0] == 7.4


def test_missing_pinned_falls_back_to_live():
    s, kind = projected_score(wish(1, "claimed", 10, age_days=2, pinned=None), NOW, K)
    assert kind == "live" and s == 8.0


def test_order_score_desc_with_tiebreaks():
    rows = [
        wish(1, "open", 10, age_days=8),       # live 2
        wish(2, "open", 10, age_days=1),       # live 9
        wish(3, "claimed", 10, 30, pinned=5),  # pinned 5
        wish(4, "open", 10, age_days=1, created=NOW - timedelta(days=1, hours=1)),  # 8.x
    ]
    out = project_wall(rows, NOW, K)
    assert [r["id"] for r in out] == [2, 4, 3, 1]


def test_equal_score_newer_created_first():
    a = wish(1, "open", 10, created=NOW - timedelta(days=2, hours=1))  # 7.x
    b = wish(2, "open", 8, created=NOW)                                  # 8 -> not equal
    # 构造真正同分：同 base 同年龄 → 不同时间不行；直接用 pinned/live 同值
    a = wish(1, "claimed", 10, age_days=5, pinned=7.0,
             created=NOW - timedelta(days=5))
    b = wish(2, "claimed", 10, age_days=3, pinned=7.0,
             created=NOW - timedelta(days=3))
    out = project_wall([a, b], NOW, K)
    assert [r["id"] for r in out] == [2, 1]


def test_every_row_carries_score_and_kind():
    out = project_wall([wish(1, "open"), wish(2, "claimed", pinned=9.0)], NOW, K)
    assert all("score" in r and "score_kind" in r for r in out)

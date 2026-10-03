"""Wall ordering projection.

- open / released：按创建时长实时线性衰减（created_at 在 release 时保留，继续老化）。
- claimed / fulfilled：使用认领瞬间钉死的 pinned_score，不再随时间或参数变化。

排序：effective score DESC，同分按 created_at ASC（更早的在前），再按 id ASC，保证确定性。
"""
from datetime import datetime
from app.modules.priority_score import live_score

LIVE_STATUSES = ("open", "released")


def effective_score(row, now: datetime, decay_per_day: float) -> float:
    """墙排序实际使用的分数。"""
    if row["status"] in LIVE_STATUSES:
        return live_score(row["base_priority"], row["created_at"], now, decay_per_day)
    return float(row["pinned_score"]) if row["pinned_score"] is not None else 0.0


def project(row, now: datetime, decay_per_day: float) -> dict:
    """给一行追加 live_score（无论状态都实时算，供详情对照）与 score（墙排序用分）。"""
    d = dict(row)
    d["live_score"] = live_score(d["base_priority"], d["created_at"], now, decay_per_day)
    d["score"] = effective_score(row, now, decay_per_day)
    return d


def order_rows(rows, now: datetime, decay_per_day: float) -> list[dict]:
    projected = [project(r, now, decay_per_day) for r in rows]
    projected.sort(key=lambda d: (-d["score"], d["created_at"], d["id"]))
    return projected

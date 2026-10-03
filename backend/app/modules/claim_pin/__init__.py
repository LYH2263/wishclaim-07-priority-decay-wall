"""Claim pinning: snapshot the decayed score at the claim instant.

钉分一旦落库即冻结：修改 decay_per_day 只影响仍 open/released 的实时排序，
已认领条目的 pinned_score 绝不重算。释放（手动或 TTL 扫回）时清除钉分，
条目回到实时衰减队列。
"""
from datetime import datetime
from app.modules.priority_score import live_score


def snapshot(base_priority: float, created_at: str | datetime,
             now: datetime, decay_per_day: float) -> dict:
    return {"pinned_score": live_score(base_priority, created_at, now, decay_per_day)}


def clear() -> dict:
    return {"pinned_score": None}

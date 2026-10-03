"""Linear age-decay priority scoring for wishes.

规则页公式与墙排序共用此实现（单一事实来源）：

    score = max(0, base_priority - decay_per_day * age_days)

其中 age_days = (now - created_at) 的秒数 / 86400，连续按天线性衰减，
分数封底为 0，永不翻负。open/released 条目每次读取时实时计算；
claimed/fulfilled 条目展示认领瞬间写入的 pinned_score 快照，不再调用本模块。
"""
from __future__ import annotations

from datetime import datetime, timezone

SECONDS_PER_DAY = 86400.0


def parse_ts(s: str) -> datetime:
    """解析 ISO-8601 时间戳，Z 结尾归一为 +00:00；裸时间按 UTC 处理。"""
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def age_days(created_at: datetime | str, now: datetime) -> float:
    """从创建到 now 的天数（连续值，非整日取整）。"""
    if isinstance(created_at, str):
        created_at = parse_ts(created_at)
    return max(0.0, (now - created_at).total_seconds() / SECONDS_PER_DAY)


def live_score(base_priority: float, created_at: datetime | str, now: datetime,
               decay_per_day: float) -> float:
    """线性衰减实时分：max(0, base - k * 年龄天数)。

    base_priority 必须 > 0（发愿望时已拦截 <=0）；
    decay_per_day >= 0（0 表示不衰减）。
    """
    if base_priority <= 0:
        raise ValueError("base_priority must be positive")
    if decay_per_day < 0:
        raise ValueError("decay_per_day must be non-negative")
    raw = base_priority - decay_per_day * age_days(created_at, now)
    return round(max(0.0, raw), 6)


def score_for_wish(wish: dict, now: datetime, decay_per_day: float) -> float:
    """从行字典计算实时分，供排序投影与认领瞬间快照共用。"""
    return live_score(float(wish["base_priority"]), wish["created_at"], now, decay_per_day)

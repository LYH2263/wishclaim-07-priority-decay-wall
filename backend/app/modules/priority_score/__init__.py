"""Priority scoring: linear daily decay from base_priority.

score(now) = max(0, base_priority - decay_per_day * age_days(created_at, now))

线性按天衰减（而非阶梯）：分数连续、公式可直接与墙顺序同钉在规则页。
"""
from datetime import datetime
from app.engines.claim_lock import parse_ts

DAY_SECONDS = 86400.0
SCORE_FLOOR = 0.0
PIN_DECIMALS = 4


def to_dt(created_at: str | datetime) -> datetime:
    return parse_ts(created_at) if isinstance(created_at, str) else created_at


def age_days(created_at: str | datetime, now: datetime) -> float:
    return max(0.0, (now - to_dt(created_at)).total_seconds() / DAY_SECONDS)


def live_score(base_priority: float, created_at: str | datetime,
               now: datetime, decay_per_day: float) -> float:
    """open/released 愿望的实时衰减分，封底 0。"""
    raw = float(base_priority) - float(decay_per_day) * age_days(created_at, now)
    return round(max(SCORE_FLOOR, raw), PIN_DECIMALS)


def valid_base_priority(base_priority) -> bool:
    """base_priority 必须为正数；<=0 或缺失一律拒发。"""
    try:
        return float(base_priority) > 0
    except (TypeError, ValueError):
        return False

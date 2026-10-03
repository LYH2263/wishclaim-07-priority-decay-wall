"""Wall ordering projection.

把愿望行投影成墙上的有序卡片：

- open / released：分数实时线性衰减（priority_score.live_score），随时间和
  decay_per_day 参数变化，score_kind="live"。
- claimed / fulfilled：使用认领瞬间落库的 pinned_score 快照，分数冻结，
  score_kind="pinned"，与详情页、我的认领同源可核对。

排序：score 降序 → created_at 新者优先 → id 大者优先（全部降序，确定性）。
created_at 为同格式 ISO-8601 UTC 字符串，字典序即时间先后。
"""
from __future__ import annotations

from datetime import datetime

from app.engines.priority_score import score_for_wish

# 钉分状态：分数冻结在认领快照；其余状态走实时衰减。
PINNED_STATUSES = ("claimed", "fulfilled")
LIVE_STATUSES = ("open", "released")


def projected_score(wish: dict, now: datetime, decay_per_day: float) -> tuple[float, str]:
    """返回 (score, kind)。pinned 行缺快照（历史脏数据）时回退实时分。"""
    if wish["status"] in PINNED_STATUSES and wish.get("pinned_score") is not None:
        return float(wish["pinned_score"]), "pinned"
    return score_for_wish(wish, now, decay_per_day), "live"


def project_wall(wishes, now: datetime, decay_per_day: float) -> list[dict]:
    """附加 score/score_kind 并按墙序排列。输入为行字典的可迭代对象。"""
    out = []
    for w in wishes:
        row = dict(w)
        row["score"], row["score_kind"] = projected_score(row, now, decay_per_day)
        out.append(row)
    out.sort(key=lambda r: (r["score"], r["created_at"], r["id"]), reverse=True)
    return out

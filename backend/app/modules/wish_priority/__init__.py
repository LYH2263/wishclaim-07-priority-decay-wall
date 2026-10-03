"""wish_priority: 优先级分数的落库与迁移（钉分快照模块）。

职责边界：
- app/engines/priority_score  纯计分（公式唯一来源）
- app/engines/wall_order      排序投影（实时分 / 钉分）
- 本模块                      schema 迁移、参数读写、认领瞬间钉分落库

钉分语义：claim 成功瞬间把当时的实时分写入 wishes.pinned_score；此后
claimed/fulfilled 的墙序分与展示分都读该快照。release（含 TTL 回收）清空
钉分，条目回到 open/released 实时衰减。修改 decay_per_day 只改参数表，
不触碰任何已落库的 pinned_score。
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.engines.priority_score import score_for_wish

DEFAULT_DECAY_PER_DAY = 1.0
DEFAULT_BASE_PRIORITY = 10.0  # 历史行迁移回填用

# 新增列: (列名, 列定义)
_NEW_COLUMNS = {
    "base_priority": "REAL",
    "created_at": "TEXT",
    "pinned_score": "REAL",
}


def migrate(c) -> None:
    """幂等迁移：为旧库补列并回填历史行；插入默认衰减参数。"""
    cols = {r["name"] for r in c.execute("PRAGMA table_info(wishes)")}
    for name, decl in _NEW_COLUMNS.items():
        if name not in cols:
            c.execute(f"ALTER TABLE wishes ADD COLUMN {name} {decl}")
    # 历史行没有创建时间/基础分：以迁移时刻为创建时间、默认基础分回填。
    c.execute(
        "UPDATE wishes SET created_at=? WHERE created_at IS NULL",
        (datetime.now(timezone.utc).isoformat(),),
    )
    c.execute(
        "UPDATE wishes SET base_priority=? WHERE base_priority IS NULL",
        (DEFAULT_BASE_PRIORITY,),
    )
    c.execute(
        "INSERT OR IGNORE INTO settings(key,value) VALUES ('decay_per_day', ?)",
        (str(DEFAULT_DECAY_PER_DAY),),
    )


def validate_base_priority(value) -> float:
    """base_priority 必须为有限正数；<=0 拒发。"""
    v = float(value)
    if not math.isfinite(v) or v <= 0:
        raise ValueError("base_priority 必须为正数")
    return v


def validate_decay_per_day(value) -> float:
    """decay_per_day 必须为非负有限数（0 表示不衰减）。"""
    v = float(value)
    if not math.isfinite(v) or v < 0:
        raise ValueError("decay_per_day 必须为非负数")
    return v


def get_decay_per_day(c) -> float:
    row = c.execute("SELECT value FROM settings WHERE key='decay_per_day'").fetchone()
    return float(row["value"]) if row else DEFAULT_DECAY_PER_DAY


def set_decay_per_day(c, value) -> float:
    """只改参数；不重算任何 pinned_score。"""
    v = validate_decay_per_day(value)
    c.execute(
        "INSERT INTO settings(key,value) VALUES ('decay_per_day', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(v),),
    )
    return v


def pin_score(c, wid: int, now: datetime) -> float:
    """认领瞬间：按当前参数计算实时分并写入钉分快照，返回该分数。"""
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if r is None:
        raise LookupError(wid)
    score = score_for_wish(dict(r), now, get_decay_per_day(c))
    c.execute("UPDATE wishes SET pinned_score=? WHERE id=?", (score, wid))
    return score


def clear_pin(c, wid: int) -> None:
    """释放（手动或 TTL 回收）时清空钉分，回到实时衰减。"""
    c.execute("UPDATE wishes SET pinned_score=NULL WHERE id=?", (wid,))

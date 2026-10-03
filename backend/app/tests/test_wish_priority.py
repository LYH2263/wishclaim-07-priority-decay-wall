import math
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from app.modules import wish_priority as wp

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)

_OLD_SCHEMA = """
CREATE TABLE wishes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
  claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT
);
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
"""


def old_db():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_OLD_SCHEMA)
    return c


def insert_wish(c, status="open", base=None, created=None, pinned=None, wid=None):
    c.execute(
        "INSERT INTO wishes(title,note,status,data_quality) VALUES (?,?,?,?)",
        ("t", "n", status, "clean"),
    )
    wid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return wid


def fresh_db():
    """建旧表后迁移，模拟启动后的库。"""
    c = old_db()
    wp.migrate(c)
    c.commit()
    return c


def test_migrate_adds_columns_and_backfills():
    c = old_db()
    wid = insert_wish(c, "open")
    c.commit()
    wp.migrate(c)
    cols = {r[1] for r in c.execute("PRAGMA table_info(wishes)")}
    assert {"base_priority", "created_at", "pinned_score"} <= cols
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    assert r["base_priority"] == wp.DEFAULT_BASE_PRIORITY
    assert r["created_at"]  # 非空回填
    assert c.execute("SELECT value FROM settings WHERE key='decay_per_day'").fetchone()["value"]


def test_migrate_is_idempotent():
    c = old_db()
    insert_wish(c)
    c.commit()
    wp.migrate(c)
    wp.migrate(c)  # 不抛错、不重复加列


def test_validate_base_priority():
    assert wp.validate_base_priority(1) == 1.0
    assert wp.validate_base_priority("3.5") == 3.5
    for bad in (0, -1, "-0.1", math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            wp.validate_base_priority(bad)


def test_validate_decay_per_day():
    assert wp.validate_decay_per_day(0) == 0.0
    assert wp.validate_decay_per_day("2") == 2.0
    for bad in (-0.01, math.nan, math.inf):
        with pytest.raises(ValueError):
            wp.validate_decay_per_day(bad)


def test_pin_writes_snapshot_of_live_score():
    c = fresh_db()
    wid = insert_wish(c)
    c.execute("UPDATE wishes SET base_priority=?, created_at=? WHERE id=?",
              (10.0, (NOW - timedelta(days=3)).isoformat(), wid))
    c.commit()
    score = wp.pin_score(c, wid, NOW)
    assert score == pytest.approx(7.0)
    c.commit()
    assert c.execute("SELECT pinned_score FROM wishes WHERE id=?", (wid,)).fetchone()[0] == pytest.approx(7.0)


def test_param_change_does_not_change_pinned_score():
    c = fresh_db()
    wid = insert_wish(c)
    c.execute("UPDATE wishes SET base_priority=?, created_at=? WHERE id=?",
              (10.0, (NOW - timedelta(days=3)).isoformat(), wid))
    c.commit()
    pinned = wp.pin_score(c, wid, NOW)
    c.commit()
    # 管理员把衰减参数从 1.0 改成 100.0
    wp.set_decay_per_day(c, 100.0)
    c.commit()
    row = c.execute("SELECT pinned_score FROM wishes WHERE id=?", (wid,)).fetchone()
    assert row[0] == pytest.approx(7.0)


def test_clear_pin_returns_row_to_live():
    c = fresh_db()
    wid = insert_wish(c, "claimed")
    c.execute("UPDATE wishes SET pinned_score=? WHERE id=?", (7.0, wid))
    c.commit()
    wp.clear_pin(c, wid)
    c.commit()
    assert c.execute("SELECT pinned_score FROM wishes WHERE id=?", (wid,)).fetchone()[0] is None


def test_set_decay_affects_only_live_recomputation():
    c = fresh_db()
    wid_open = insert_wish(c, "open")
    wid_claimed = insert_wish(c, "claimed")
    for wid in (wid_open, wid_claimed):
        c.execute("UPDATE wishes SET base_priority=?, created_at=? WHERE id=?",
                  (10.0, (NOW - timedelta(days=3)).isoformat(), wid))
    c.execute("UPDATE wishes SET pinned_score=? WHERE id=?", (7.0, wid_claimed))
    c.commit()
    wp.set_decay_per_day(c, 5.0)
    c.commit()
    # open 条目用新参数实时算 → 封底 0；claimed 钉分不动
    assert wp.pin_score(c, wid_open, NOW) == 0.0  # 重新 pin 才会落新分
    assert c.execute("SELECT pinned_score FROM wishes WHERE id=?",
                     (wid_claimed,)).fetchone()[0] == 7.0

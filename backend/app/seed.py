from datetime import datetime, timedelta, timezone

from app.db import connect
from app.modules import wish_priority as wp


def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS wishes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
      claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,
      base_priority REAL, created_at TEXT, pinned_score REAL
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    # 兼容旧库：缺列则补齐并回填（幂等）。
    wp.migrate(c)
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        ts = datetime.now(timezone.utc)
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,"
            "data_quality,base_priority,created_at,pinned_score) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean",
                 10.0, (ts - timedelta(days=1)).isoformat(), None),
                ("围巾", "羊毛", "open", None, None, None, "clean",
                 8.0, (ts - timedelta(hours=12)).isoformat(), None),
                ("高优待领", "base=20", "open", None, None, None, "clean",
                 20.0, (ts - timedelta(days=5)).isoformat(), None),
                ("已认领钉分样例", "钉分应冻结", "claimed", "alice",
                 (ts - timedelta(hours=2)).isoformat(),
                 (ts + timedelta(hours=22)).isoformat(), "clean",
                 10.0, (ts - timedelta(days=4)).isoformat(), 6.0),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty",
                 5.0, ts.isoformat(), None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty",
                 10.0, "2020-01-01T00:00:00+00:00", None),
            ],
        )
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('ttl_seconds','86400')")
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
        c.commit()
    c.close()

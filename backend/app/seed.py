from datetime import datetime, timezone

from app.db import connect


def _has_column(c, table: str, col: str) -> bool:
    return any(r["name"] == col for r in c.execute(f"PRAGMA table_info({table})"))


def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS wishes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
      claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,
      base_priority REAL NOT NULL DEFAULT 100,
      created_at TEXT NOT NULL DEFAULT '',
      pinned_score REAL
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    # ---- 轻量迁移：旧库补列并回填 ----
    if not _has_column(c, "wishes", "base_priority"):
        c.execute("ALTER TABLE wishes ADD COLUMN base_priority REAL")
    if not _has_column(c, "wishes", "created_at"):
        c.execute("ALTER TABLE wishes ADD COLUMN created_at TEXT")
    if not _has_column(c, "wishes", "pinned_score"):
        c.execute("ALTER TABLE wishes ADD COLUMN pinned_score REAL")
    legacy_now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE wishes SET base_priority=100 WHERE base_priority IS NULL OR base_priority<=0")
    c.execute("UPDATE wishes SET created_at=? WHERE created_at IS NULL OR created_at=''", (legacy_now,))

    # 设置项幂等补齐：旧库同样需要 decay_per_day
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('ttl_seconds','86400')")
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
    c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES ('decay_per_day','2')")

    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,"
            "base_priority,created_at,pinned_score) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean", 100, legacy_now, None),
                ("围巾", "羊毛", "open", None, None, None, "clean", 60, legacy_now, None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty", 30, legacy_now, None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", 80, "2020-01-01T00:00:00+00:00", None),
            ],
        )
    c.commit()  # 无条件提交：迁移补列回填与设置项在旧库路径下也必须落盘
    c.close()

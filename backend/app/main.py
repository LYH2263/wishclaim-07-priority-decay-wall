from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.engines.wall_order import project_wall, projected_score
from app.modules import wish_priority as wp

app = FastAPI(title="Wishclaim", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def ttl(c):
    row = c.execute("SELECT value FROM settings WHERE key='ttl_seconds'").fetchone()
    return int(row["value"] if row else 86400)

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
                      (rel["status"], None, None, None, r["id"]))
            # TTL 回收：钉分作废，回到实时衰减排序。
            wp.clear_pin(c, r["id"])

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    k = wp.get_decay_per_day(c)
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes")]
    out = project_wall(rows, now(), k)
    c.close(); return out

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    row = dict(r)
    # 与墙同一投影：open/released 实时分，claimed/fulfilled 钉分，可与墙序核对。
    row["score"], row["score_kind"] = projected_score(row, now(), wp.get_decay_per_day(c))
    c.close(); return row

class WishIn(BaseModel):
    title: str
    note: str = ""
    base_priority: float = 10.0

@app.post("/api/wishes")
def create_wish(body: WishIn):
    try:
        base = wp.validate_base_priority(body.base_priority)
    except ValueError as e:
        raise HTTPException(422, str(e))
    c = connect()
    cur = c.execute(
        "INSERT INTO wishes(title,note,status,data_quality,base_priority,created_at) "
        "VALUES (?,?,?,?,?,?)",
        (body.title, body.note, "open", "clean", base, now().isoformat()),
    )
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid, "base_priority": base}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    p = lock_payload(body.claimer, now(), ttl(c))
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], wid))
    # 认领瞬间写入 score 快照（钉分），此后不随时间/参数变化。
    p["pinned_score"] = wp.pin_score(c, wid, now())
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    # 释放即作废钉分，重新按创建时长实时衰减。
    wp.clear_pin(c, wid)
    c.commit(); c.close(); return {"ok": True, "status": "released"}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    c.execute("UPDATE wishes SET status='fulfilled' WHERE id=?", (wid,))
    # pinned_score 原样保留：fulfilled 继续展示认领钉分。
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    k = wp.get_decay_per_day(c)
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]
    for row in rows:
        row["score"], row["score_kind"] = projected_score(row, now(), k)
    rows.sort(key=lambda r: (r["score"], r["created_at"], r["id"]), reverse=True)
    c.close(); return rows

@app.get("/api/done")
def done():
    c = connect()
    k = wp.get_decay_per_day(c)
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]
    out = project_wall(rows, now(), k)
    c.close(); return out

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

class SettingsIn(BaseModel):
    decay_per_day: float | None = None

@app.patch("/api/settings")
def update_settings(body: SettingsIn):
    """改衰减参数：只影响仍 open/released 的实时排序，不重算任何钉分。"""
    c = connect()
    if body.decay_per_day is not None:
        try:
            wp.set_decay_per_day(c, body.decay_per_day)
        except ValueError as e:
            c.close(); raise HTTPException(422, str(e))
    c.commit()
    rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}
    c.close(); return rows

@app.get("/api/rules")
def rules():
    c = connect(); k = wp.get_decay_per_day(c); c.close()
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "priority_formula": "score = max(0, base_priority − decay_per_day × 已创建天数)",
        "priority_decay": f"open/released 按创建时长线性按天衰减，当前 decay_per_day={k}",
        "priority_pinned": "认领瞬间把当时分数写入钉分快照，claimed/fulfilled 的墙序与详情均展示钉分；释放后回到实时衰减",
        "priority_param": "修改 decay_per_day 只影响仍 open/released 的排序，不改变任何已认领钉分",
        "base_priority": "发愿望必须带 base_priority 且为正数（>0），否则拒发",
        "wall_order": "墙按 score 降序；分数相同则创建时间新者优先，再相同则 id 大者优先",
    }

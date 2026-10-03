from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.modules import claim_pin
from app.modules.priority_score import valid_base_priority
from app.modules.wall_order import order_rows, project

app = FastAPI(title="Wishclaim", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def _setting(key: str, default: str) -> str:
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone(); c.close()
    return row["value"] if row else default

def ttl():
    return int(_setting("ttl_seconds", "86400"))

def decay_per_day() -> float:
    # 改这里（settings.decay_per_day）只影响仍 open/released 的实时排序，不回写钉分
    return float(_setting("decay_per_day", "2"))

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            # TTL 扫回开放队列：钉分一并清除，重新参与实时衰减
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, pinned_score=? WHERE id=?",
                      (rel["status"], None, None, None, None, r["id"]))

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes")]
    c.close()
    return order_rows(rows, now(), decay_per_day())

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone(); c.close()
    if not r: raise HTTPException(404, "not found")
    # 同时返回 score（已认领=钉分）与 live_score（持续衰减的假想分），详情页并列核对
    return project(r, now(), decay_per_day())

class WishIn(BaseModel):
    title: str
    note: str = ""
    base_priority: float

@app.post("/api/wishes")
def create_wish(body: WishIn):
    if not valid_base_priority(body.base_priority):
        raise HTTPException(422, "base_priority 必须为正数（> 0），<= 0 拒发")
    c = connect()
    cur = c.execute(
        "INSERT INTO wishes(title,note,status,data_quality,base_priority,created_at,pinned_score) "
        "VALUES (?,?,?,?,?,?,?)",
        (body.title, body.note, "open", "clean", body.base_priority, now().isoformat(), None),
    )
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

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
    ts = now()
    p = lock_payload(body.claimer, ts, ttl())
    # 认领瞬间写入 score 快照（钉分），此后与时间/衰减参数脱钩
    pin = claim_pin.snapshot(r["base_priority"], r["created_at"], ts, decay_per_day())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=?, pinned_score=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], pin["pinned_score"], wid))
    c.commit(); c.close(); return {**p, **pin}

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL, "
              "pinned_score=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    c.execute("UPDATE wishes SET status='fulfilled' WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]
    c.close()
    # 我的认领：claimed 按钉分展示
    return order_rows(rows, now(), decay_per_day())

@app.get("/api/done")
def done():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]
    c.close()
    return order_rows(rows, now(), decay_per_day())

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    dpd = decay_per_day()
    formula = f"score = max(0, base_priority − {dpd:g} × 存活天数)"
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "priority_formula": formula,
        "priority_decay": "线性按天衰减（非阶梯）；open/released 按创建时长实时计算",
        "priority_pin": "认领瞬间把当时分数快照为钉分；墙对已认领条目按钉分排序，详情页钉分与实时分并列可核对",
        "priority_param": f"改衰减参数（当前 {dpd:g}/天）只影响仍 open/released 的排序，已认领钉分不变",
        "base_priority_rule": "base_priority 必须 > 0，否则拒发",
    }

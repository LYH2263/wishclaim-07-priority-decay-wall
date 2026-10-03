import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # db_path 在调用时读环境变量，无需重新导入；但确保全新进程态。
    from app import db, seed  # noqa
    assert str(tmp_path) in str(db.db_path())
    from app.main import app
    with TestClient(app) as c:
        yield c


def _create(client, title, base, days_old=0):
    r = client.post("/api/wishes", json={"title": title, "note": "",
                                         "base_priority": base})
    assert r.status_code == 200, r.text
    wid = r.json()["id"]
    if days_old:
        # 通过直接改库把创建时间往回拨。
        from app.db import connect
        from datetime import datetime, timedelta, timezone
        c = connect()
        ts = (datetime.now(timezone.utc) - timedelta(days=days_old)).isoformat()
        c.execute("UPDATE wishes SET created_at=? WHERE id=?", (ts, wid))
        c.commit(); c.close()
    return wid


def test_health(client):
    assert client.get("/api/health").json()["ok"] is True


def test_create_rejects_nonpositive_base_priority(client):
    for bad in (0, -5):
        r = client.post("/api/wishes", json={"title": "x", "base_priority": bad})
        assert r.status_code == 422


def test_create_accepts_positive_base_priority(client):
    r = client.post("/api/wishes", json={"title": "x", "base_priority": 3.5})
    assert r.status_code == 200 and r.json()["base_priority"] == 3.5


def test_rules_expose_formula_and_param(client):
    r = client.get("/api/rules").json()
    assert "max(0" in r["priority_formula"]
    assert "decay_per_day" in r["priority_decay"]


def test_wall_rows_carry_score_and_kind(client):
    _create(client, "a", 10, days_old=2)
    rows = client.get("/api/wishes").json()
    assert all("score" in r and "score_kind" in r for r in rows)
    assert {r["score_kind"] for r in rows} <= {"live", "pinned"}


def test_claim_writes_pinned_snapshot(client):
    wid = _create(client, "a", 10, days_old=3)
    before = client.get(f"/api/wishes/{wid}").json()["score"]
    assert before == pytest.approx(7.0, abs=0.01)
    r = client.post(f"/api/wishes/{wid}/claim", json={"claimer": "alice"})
    pinned = r.json()["pinned_score"]
    assert pinned == pytest.approx(7.0, abs=0.01)
    detail = client.get(f"/api/wishes/{wid}").json()
    assert detail["score_kind"] == "pinned" and detail["score"] == pinned


def test_param_change_reorders_only_open_not_pinned(client):
    open_old = _create(client, "open-old", 10, days_old=8)   # k=1 时 2 分
    open_new = _create(client, "open-new", 10, days_old=1)   # k=1 时 9 分
    claimed = _create(client, "claimed", 10, days_old=8)
    client.post(f"/api/wishes/{claimed}/claim", json={"claimer": "a"})
    pinned = client.get(f"/api/wishes/{claimed}").json()["score"]

    # 改参数前：new(9) > claimed(pin 2) ≈ open-old(2)
    order = [r["id"] for r in client.get("/api/wishes").json()]
    assert order.index(open_new) < order.index(open_old)

    # 改参数为 0：两个 open 都回到 base=10，created 新者靠前；钉分不变
    client.patch("/api/settings", json={"decay_per_day": 0})
    rows = {r["id"]: r for r in client.get("/api/wishes").json()}
    assert rows[claimed]["score"] == pytest.approx(pinned)
    assert rows[claimed]["score_kind"] == "pinned"
    assert rows[open_old]["score"] == pytest.approx(10.0)
    assert rows[open_new]["score"] == pytest.approx(10.0)

    # 参数改大：open-old 实时封底 0，钉分依然不动
    client.patch("/api/settings", json={"decay_per_day": 100})
    rows = {r["id"]: r for r in client.get("/api/wishes").json()}
    assert rows[open_old]["score"] == 0.0 and rows[open_old]["score_kind"] == "live"
    assert rows[claimed]["score"] == pytest.approx(pinned)


def test_release_clears_pin_back_to_live(client):
    wid = _create(client, "a", 10, days_old=8)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "a"})
    pinned = client.get(f"/api/wishes/{wid}").json()["score"]
    client.post(f"/api/wishes/{wid}/release", json={})
    detail = client.get(f"/api/wishes/{wid}").json()
    assert detail["status"] == "released"
    assert detail["score_kind"] == "live"
    assert detail["pinned_score"] is None
    assert detail["score"] == pytest.approx(2.0, abs=0.01)
    assert detail["score"] != pinned


def test_fulfill_keeps_pinned_score(client):
    wid = _create(client, "a", 10, days_old=8)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "a"})
    pinned = client.get(f"/api/wishes/{wid}").json()["score"]
    client.post(f"/api/wishes/{wid}/fulfill", json={})
    detail = client.get(f"/api/wishes/{wid}").json()
    assert detail["status"] == "fulfilled"
    assert detail["score_kind"] == "pinned" and detail["score"] == pinned


def test_wall_and_detail_use_same_score(client):
    wid = _create(client, "a", 10, days_old=2)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "a"})
    wall = {r["id"]: r for r in client.get("/api/wishes").json()}[wid]
    detail = client.get(f"/api/wishes/{wid}").json()
    assert wall["score"] == detail["score"]
    assert wall["score_kind"] == detail["score_kind"] == "pinned"


def test_mine_shows_pinned_score(client):
    wid = _create(client, "a", 10, days_old=4)
    client.post(f"/api/wishes/{wid}/claim", json={"claimer": "bob"})
    rows = client.get("/api/mine", params={"claimer": "bob"}).json()
    assert len(rows) == 1
    assert rows[0]["score_kind"] == "pinned"
    assert rows[0]["score"] == client.get(f"/api/wishes/{wid}").json()["score"]


def test_decay_param_validation(client):
    r = client.patch("/api/settings", json={"decay_per_day": -1})
    assert r.status_code == 422

# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

0-1：`wish_comment` / `secret_santa` / `price_cap`。

## 优先级衰减排墙

线性按天衰减（非阶梯）：

```
score = max(0, base_priority − decay_per_day × 存活天数)
```

- `base_priority` 必须 > 0，否则拒发；`decay_per_day` 在 `settings` 表（默认 2）。
- open / released 按创建时长实时衰减排序；released 保留 `created_at` 继续老化。
- 认领瞬间把当时分数快照为 `pinned_score`（钉分）：墙、详情、我的认领对已认领条目一律读钉分。
- 详情页并列展示墙序分（钉分）与实时衰减分，可核对。
- 改 `decay_per_day` 只影响仍 open/released 的排序，已认领钉分绝不重算；释放/TTL 扫回时清钉分。

模块：`modules/priority_score`（计分）、`modules/wall_order`（排序投影）、`modules/claim_pin`（钉分落库），测例在 `app/tests/`。

# rankings

网文公开榜单聚合管道：抓取起点 / 纵横 / 刺猬猫公开榜页元数据，产出 `docs/rankings.json`，供 iReader 等客户端经 **jsDelivr** 拉取。

## 合规说明

- 仅聚合公开榜单上的**书名、作者、分类、封面链接、正版阅读页链接、热度文案**
- **不存储**章节正文；不链接盗版站点
- 数据著作权归原作者与各平台；本仓库仅作发现/推荐用途
- 抓取低频（每日一次）、限速，单站失败不影响其它站

## 输出

`docs/rankings.json`，Schema 与 App `RankingsResponse` 兼容（含可选 `source` / `sourceId`）。

客户端：

```
https://cdn.jsdelivr.net/gh/Feiladin/rankings@main/docs/rankings.json
```

## 本地运行

```bash
pip install -r requirements.txt
python scripts/merge.py --dry-run
python scripts/merge.py
```

> 说明：部分源站对非机房 IP 有 WAF/5xx，日常更新以 GitHub Actions（海外 runner）为准。

## 更新

GitHub Actions：每日 06:00 UTC 执行 `scripts/merge.py`，JSON 有 diff 则提交。亦可手动 `workflow_dispatch`。

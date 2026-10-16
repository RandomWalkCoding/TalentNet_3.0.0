# Stage 3 Verification - 评分服务增强

## 分支

- `feature/stage-3`
- 基于 `feature/stage-2`

## 后端完成项

- 清理 `RiskScoringService` 中文乱码文案
- 评分模型升级为 `rules-v2`
- 引入评分输入快照 `input_snapshot`
- 引入证据新鲜度：
  - `fresh_count`
  - `stale_count`
  - `age_days`
- 引入来源权重：
  - LinkedIn / 脉脉 / 官网 / 招聘 / arXiv / 专利 / manual
- 引入人工确认状态：
  - 已确认提高置信度
  - 未确认降低置信度并进入待核实说明
- 低置信度自动进入 `needs_review`
- 保存评分输入摘要、特征权重、证据引用
- 增加未确认/过期证据测试

## 前端完成项

- 评分卡展示评分输入摘要
- 展示证据总数、已确认、待确认、近期证据、过期证据、平均置信度
- 展示评分特征、权重和对应 evidence ids
- 展示待核实原因和限制说明
- 刷新评分错误态中文化
- 前端只展示后端评分结果，不计算风险分

## 验证命令

```powershell
cd backend
$py='C:\Users\HUAWEI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pytest
& $py -m compileall app tests

cd ..\frontend
npm.cmd install
npm.cmd run build
```

## 验证结果

- Backend tests: `27 passed`
- Backend compileall: passed
- Frontend build: passed
- Runtime smoke:
  - `POST /api/candidates/cand_lin_chen/refresh-score` 返回 `model_version=rules-v2`
  - 返回 `input_snapshot.evidence_count=2`
  - 返回 `input_snapshot.confirmed_count=2`
  - 候选人详情中的 latest_score 与刷新结果一致
  - `/candidates/cand_lin_chen` 返回 200，页面包含“评分输入摘要”

## 清理要求

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- Python `__pycache__`
- `.pytest_cache`

以上产物只用于阶段验收，不进入仓库。

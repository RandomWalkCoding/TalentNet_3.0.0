# Stage 1 Verification - 真实证据录入链路

## 分支

- `feature/stage-1`
- 基于 `feature/stage-0`

## 后端完成项

- 新增 `POST /api/evidence`
- 新增 `PATCH /api/evidence/{id}`
- 新增 `POST /api/evidence/{id}/confirm`
- 新增临时去重逻辑：同一候选人、同一来源下，URL 重复或标题+摘要重复会返回 `409 EVIDENCE_DUPLICATED`
- 证据确认后由后端调用 `RiskScoringService.refresh_candidate_score`
- BrowserTask 草稿新增 `PATCH /api/browser-tasks/{id}/evidence-draft`，确认前可编辑
- BrowserTask 证据确认复用统一证据写入逻辑

## 前端完成项

- 候选人详情页新增“新增证据”表单
- 候选人详情页展示证据确认状态、来源、置信度、截图路径
- 待确认的证据可在候选人详情页确认，并触发后端刷新评分
- 浏览器任务页支持编辑 evidence draft 后确认入库
- 前端只调用 API，不直接计算评分

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

- Backend tests: `23 passed`
- Backend compileall: passed
- Frontend build: passed
- Runtime smoke:
  - `GET /api/health` 返回 `ok`
  - `POST /api/evidence` 创建成功
  - `POST /api/evidence/{id}/confirm` 后 `confirmed_by_user=true`
  - 证据确认后候选人最新评分 ID 变化，说明后端已刷新评分
  - `PATCH /api/browser-tasks/{id}/evidence-draft` 可更新草稿
  - `GET /candidates/cand_zhou_yu` 返回 200，页面包含“新增证据”

## 清理要求

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- Python `__pycache__`
- `.pytest_cache`

以上产物只用于阶段验收，不进入仓库。

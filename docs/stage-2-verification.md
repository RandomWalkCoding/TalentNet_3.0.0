# Stage 2 Verification - LLM Gateway 与真实模型调用

## 分支

- `feature/stage-2`
- 基于 `feature/stage-1`

## 后端完成项

- 新增 `LLMGateway`
- 支持 OpenAI-compatible 配置：
  - `TALENTNET_LLM_PROVIDER`
  - `TALENTNET_LLM_MODEL`
  - `TALENTNET_LLM_API_KEY`
  - `TALENTNET_LLM_BASE_URL`
  - `TALENTNET_LLM_TIMEOUT_SECONDS`
- 新增 `GET /api/llm/status`
- `generate-summary` 与 `generate-outreach` 通过 Gateway 生成
- 无 API Key、模型失败、JSON 不合法、证据引用不合法时自动降级到本地结构化模板
- LLM 输出必须引用当前候选人的 evidence id
- 增加 OpenAI-compatible mock 测试

## 前端完成项

- AI 面板展示模型配置状态
- AI 面板展示生成中、失败、真实模型/本地降级提示
- AI 摘要展示 cited evidence
- 外联话术仍可编辑和复制
- 前端只调用后端 API，不持有 LLM API Key

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

- Backend tests: `25 passed`
- Backend compileall: passed
- Frontend build: passed
- Runtime smoke:
  - `GET /api/llm/status` 返回 `provider=local`、`configured=false`
  - `POST /api/candidates/cand_lin_chen/generate-summary` 返回 `used_fallback=true`
  - `POST /api/candidates/cand_lin_chen/generate-outreach` 返回 3 条话术
  - `/candidates/cand_lin_chen` 返回 200，页面包含“模型状态”

## 清理要求

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- Python `__pycache__`
- `.pytest_cache`

以上产物只用于阶段验收，不进入仓库。

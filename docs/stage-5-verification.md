# Stage 5 Verification - AI 浏览器任务真实执行

## 分支

- `feature/stage-5`
- 基于 `feature/stage-4`

## 后端完成项

- BrowserTask 增加执行字段：
  - `execution_log`
  - `page_title`
  - `page_url`
  - `screenshot_path`
- 创建任务后由后端尝试 Playwright 真实打开目标 URL 或搜索 URL
- 读取页面 title、最终 URL、可见文本
- 截图保存到 `artifacts/browser-tasks/{task_id}.png`
- 根据页面可见文本生成 evidence draft
- Playwright 不可用或目标站失败时，自动生成低置信度降级草稿，任务仍可运行
- 新增 `POST /api/browser-tasks/{id}/retry`
- 保留草稿编辑、确认入库、评分刷新链路
- 增加成功、失败降级、重试测试

## 前端完成项

- 任务页展示执行日志
- 展示页面标题、URL、截图路径
- 展示失败信息和降级草稿
- 支持任务重试
- 保留草稿编辑后确认入库
- 明确合规提示：不保存密码、不绕过验证码、不批量抓取

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

- Backend tests: `33 passed`
- Backend compileall: passed
- Frontend build: passed
- Runtime smoke:
  - `POST /api/browser-tasks` 返回 `waiting_user`
  - 返回 `execution_log`
  - 返回 `evidence_draft`
  - `/browser-tasks` 返回 200
  - 页面包含“执行日志”和“重试”

## 清理要求

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- `artifacts/browser-tasks`
- Python `__pycache__`
- `.pytest_cache`

以上产物只用于阶段验收，不进入仓库。

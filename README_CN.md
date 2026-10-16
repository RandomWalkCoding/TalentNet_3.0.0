# TalentNet 竞对人才情报系统

TalentNet 是一个 AI 辅助的竞对人才情报 Demo 项目，面向中大型科技公司的技术招聘团队，用于监测竞对核心人才变化、评估候选人流动风险、推荐挖猎时机，并通过反馈数据形成闭环。

本项目采用前后端分离架构：前端负责页面展示与交互，后端负责数据、AI 编排、浏览器任务、评分、反馈和分析。

## 核心能力

- 情报总览：查看监测公司、高风险候选人和 API 状态。
- 候选人详情：展示候选人基础信息、证据链、风险评分和 AI 解释。
- 风险评分：后端基于 evidence 规则计算 `risk_score`、`confidence_score`、`risk_level`。
- 人才猎场：将候选人加入每日行动列表，支持筛选、排序和状态更新。
- 反馈闭环：记录触达结果，支持 `bad_prediction` 写入坏例库。
- AI 浏览器任务：Demo 阶段生成可确认的网页证据草稿，不做批量抓取。
- AI 开场白：后端生成 3 个可编辑触达话术版本，不自动发送。
- 效能分析：展示高风险覆盖率、猎场加入率、触达率、反馈率、转化率等指标。

## 技术栈

### 前端

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui 配置
- lucide-react

### 后端

- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- pytest
- Playwright Python 包

### Demo 数据

项目启动时会使用 SQLite 和内置种子数据，包含：

- 竞对公司
- 候选人
- 证据
- 初始风险评分

## 项目结构

```text
TalentNet/
  backend/
    app/
      api/
      core/
      models/
      repositories/
      schemas/
      services/
    scripts/
    tests/
  frontend/
    app/
    components/
    lib/
  docs/
  start.ps1
  start.sh
```

## 一键启动

Windows PowerShell：

```powershell
.\start.ps1
```

macOS / Linux / Git Bash：

```bash
./start.sh
```

启动后打开：

```text
http://127.0.0.1:3000
```

后端健康检查：

```text
http://127.0.0.1:8000/api/health
```

如果 `3000` 或 `8000` 端口被占用，请先关闭已有本地服务。

## 手动启动

### 后端

```bash
cd backend
python -m pip install -r requirements.txt
python -m scripts.reset_seed
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## Demo 演示路径

推荐演示顺序：

1. 打开 `/dashboard` 查看情报总览。
2. 点击高风险候选人 `林晨`。
3. 查看候选人基础信息、证据链和风险评分。
4. 点击“加入人才猎场”。
5. 点击“生成建议”，查看 AI 解释和 3 个开场白。
6. 编辑或复制一个开场白。
7. 在反馈面板记录触达结果。
8. 打开 `/talent-pool` 查看猎场状态。
9. 打开 `/analytics` 查看反馈漏斗和指标变化。

详细演示文档：

```text
docs/demo-walkthrough.md
```

## API 概览

### 基础数据

```text
GET /api/health
GET /api/companies
GET /api/candidates
GET /api/candidates/{id}
GET /api/evidence?candidate_id={id}
```

### 风险评分

```text
GET  /api/candidates/{id}/score
POST /api/candidates/{id}/refresh-score
```

### 人才猎场

```text
POST   /api/candidates/{id}/add-to-pool
GET    /api/talent-pool
PATCH  /api/talent-pool/{id}
DELETE /api/talent-pool/{id}
```

### 反馈闭环

```text
POST /api/feedback
GET  /api/feedback?candidate_id={id}
```

### 浏览器任务

```text
POST /api/browser-tasks
GET  /api/browser-tasks
GET  /api/browser-tasks/{id}
POST /api/browser-tasks/{id}/cancel
POST /api/browser-tasks/{id}/confirm-evidence
```

### AI 解释与开场白

```text
POST /api/candidates/{id}/generate-summary
POST /api/candidates/{id}/generate-outreach
```

### 效能分析

```text
GET /api/analytics/summary
```

## 合规边界

当前项目是 Demo 版本：

- 不批量抓取 LinkedIn、脉脉等平台数据。
- 不绕过登录、验证码、风控或平台权限。
- 不保存用户密码。
- 浏览器任务只生成待确认的 evidence draft。
- 证据必须由用户确认后才会入库。
- AI 开场白只供用户编辑参考，系统不会自动发送。

## 阶段分支

项目按阶段开发，每个阶段一个独立分支：

```text
feature/stage-0  项目初始化
feature/stage-1  基础数据与种子数据
feature/stage-2  风险评分引擎
feature/stage-3  人才猎场
feature/stage-4  反馈闭环
feature/stage-5  AI 浏览器任务
feature/stage-6  LLM 解释与开场白
feature/stage-7  效能分析
feature/stage-8  打磨与演示
```

最终可演示版本位于：

```text
feature/stage-8
```

## 测试

后端测试：

```bash
cd backend
python -m pytest
```

前端构建：

```bash
cd frontend
npm run build
```

当前验证状态：

```text
后端测试：20 passed
前端构建：Compiled successfully
```

## 后续演进方向

- 接入真实 OpenAI 或兼容 LLM 网关。
- 将 SQLite 迁移到 PostgreSQL。
- 引入 Redis / Celery 处理异步任务。
- 接入真实 Playwright 浏览器会话。
- 增加企业权限、SSO、多租户隔离。
- 增加更完整的审计日志和数据安全策略。
- 将 Demo 浏览器任务升级为合规 API / 数据服务商接入。

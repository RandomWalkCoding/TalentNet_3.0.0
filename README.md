# TalentNet

TalentNet 是一个面向技术招聘团队的 AI 辅助竞对人才情报工作台。它把竞对公司监测、候选人资料、证据链、风险评分、AI 搜索、人才猎场和跟进分析放在同一个本地应用中，帮助招聘顾问从“发现线索”推进到“记录反馈”。

当前版本定位为可本地运行的 MVP Demo，适合产品演示、流程验证和后续功能开发。

## 核心能力

- **公司与候选人库**：创建、编辑、筛选候选人，支持 CSV 导入。
- **证据链管理**：手工记录证据，上传 TXT、MD、CSV、PDF、DOCX、XLSX、JSON、HTML 等文件，并下载原文件。
- **风险评分**：根据候选人证据计算风险分、置信度和风险等级，并展示可追溯解释。
- **AI 搜索与网页核查**：输入自然语言人才画像，生成搜索计划和候选人线索；网页结果需要人工审核后入库。
- **人才猎场**：将值得跟进的人加入行动列表，更新跟进状态并登记反馈。
- **AI 建议**：生成候选人摘要、风险解释和可编辑联系话术；未配置模型时自动使用本地规则模板。
- **分析看板**：查看高风险覆盖率、入猎场率、触达率、反馈率、转化率、趋势和漏斗。
- **关系线索**：发现同公司同部门的疑似关系，支持人工确认或否定并保留审核结果。
- **本地工作区**：支持演示身份切换、角色限制、操作审计、模型调用记录和数据源状态。

## 技术架构

```text
浏览器
  │
  └── Next.js 15 + React 19 + Tailwind CSS
          │ REST API
          ▼
      FastAPI + SQLAlchemy
          │
          ├── SQLite 本地演示数据库
          ├── 文件上传与文本提取
          ├── 规则评分、分析与审计
          ├── 可选 OpenAI 兼容 LLM Gateway
          └── 可选 Playwright 浏览器任务
```

主要目录：

```text
backend/       FastAPI API、业务服务、数据模型、测试
frontend/      Next.js 页面和交互组件
docs/          产品说明、演示步骤、审查记录
scripts/       启动辅助脚本
start.bat      Windows 双击启动入口
start.ps1      Windows PowerShell 启动脚本
start.sh       macOS/Linux 启动脚本
```

## 快速开始

### Windows

最简单的方式是双击项目根目录的 `start.bat`。它会自动准备依赖、构建前端、启动 FastAPI 和 Next.js，并在页面就绪后打开浏览器。

也可以在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -OpenBrowser
```

### macOS / Linux

```bash
chmod +x ./start.sh
./start.sh
```

启动后访问：

- 应用：<http://127.0.0.1:3025>
- API 健康检查：<http://127.0.0.1:8015/api/health>
- Swagger API 文档：<http://127.0.0.1:8015/docs>

默认服务只监听本机回环地址。按 `Ctrl+C` 可停止服务。

端口冲突时，Windows 可以指定端口：

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1 -BackendPort 8016 -FrontendPort 3026 -OpenBrowser
```

macOS/Linux 可以使用环境变量：

```bash
TALENTNET_BACKEND_PORT=8016 TALENTNET_FRONTEND_PORT=3026 ./start.sh
```

## 演示流程

1. 打开「AI 搜索候选人」，输入目标人才画像并运行一次搜索。
2. 在结果中核对来源，将可信线索加入人才库或人才猎场。
3. 打开候选人详情，查看风险评分、证据链和 AI 建议。
4. 上传一份简历或项目材料，确认提取结果并保存为证据。
5. 在人才猎场更新跟进状态，登记触达和后续反馈。
6. 在「效能分析」查看漏斗、趋势和反馈覆盖率。
7. 在「组织关系」查看疑似关系并进行人工确认或否定。

完整步骤见 [docs/demo-walkthrough.md](docs/demo-walkthrough.md)，功能边界见 [docs/local-demo-audit.md](docs/local-demo-audit.md)。

## 数据与配置

启动脚本默认使用独立的 `backend/talentnet-local-demo.db`，会自动初始化演示数据。它不会修改原有的 `backend/talentnet.db`。上传文件保存在 `backend/data/uploads/`。

如需使用真实模型，在根目录或 `backend/` 下创建 `.env`，参考 [.env.example](.env.example) 配置 OpenAI 兼容接口：

```dotenv
TALENTNET_LLM_PROVIDER=minimax
TALENTNET_LLM_MODEL=MiniMax-M2
TALENTNET_LLM_API_KEY=your-api-key
TALENTNET_LLM_BASE_URL=https://api.minimaxi.com/v1
```

密钥只在后端读取，不会返回给前端。未配置模型时，系统使用本地生成路径，核心演示流程仍可运行。

## 开发与验证

环境要求：Python 3.12、Node.js 20+、npm。

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm.cmd run build
npm.cmd run lint
npm.cmd run typecheck
```

后端测试覆盖 API、数据导入、证据上传、评分、网页任务降级、反馈分析、身份权限和关系审核等流程。

## 当前边界

- 网页核查取决于目标站点可达性、登录状态和访问规则，不保证所有公开页面都能读取。
- AI 搜索结果和网页证据需要人工核对后入库，系统不会把失败抓取标记为已验证事实。
- AI 话术只生成和复制，不会自动发送邮件或社交平台消息。
- 当前关系推断只提供同公司同部门的弱线索，不代表汇报、合作或私人关系。
- 图片型 PDF、扫描件和复杂附件需要额外 OCR 或解析服务。
- 本地身份切换只用于 Demo，不适合作为生产环境认证方案。

## License

本仓库当前主要用于内部产品验证和本地演示。正式对外发布前，请补充项目许可证、第三方依赖声明和数据使用说明。


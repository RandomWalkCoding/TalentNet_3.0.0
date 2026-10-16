# Stage 4 Verification - 候选人/公司真实录入与导入

## 分支

- `feature/stage-4`
- 基于 `feature/stage-3`

## 后端完成项

- 新增 `POST /api/companies`
- 新增 `PATCH /api/companies/{id}`
- 新增 `POST /api/candidates`
- 新增 `PATCH /api/candidates/{id}`
- 新增 `POST /api/candidates/import-csv`
- CSV 导入支持字段：
  - `name`
  - `company_name`
  - `industry`
  - `website`
  - `title`
  - `department`
  - `location`
  - `domain`
  - `profile_summary`
- 公司按名称去重
- 候选人按“姓名 + 公司”去重
- 导入结果返回 created / duplicate / failed 报告
- 新建或编辑候选人后由后端刷新评分
- 新增依赖 `python-multipart==0.0.20` 用于 FastAPI multipart 上传

## 前端完成项

- 公司页新增“新建公司”入口
- 候选人页新增“新建候选人”入口
- 候选人页新增 CSV 上传入口
- 导入后展示新增、重复、失败数量
- 前端只调用 API，不直接写数据库

## 验证命令

```powershell
cd backend
$py='C:\Users\HUAWEI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pip install -r requirements.txt
& $py -m pytest
& $py -m compileall app tests

cd ..\frontend
npm.cmd install
npm.cmd run build
```

## 验证结果

- Backend tests: `31 passed`
- Backend compileall: passed
- Frontend build: passed
- Runtime smoke:
  - `POST /api/companies` 可创建公司
  - `POST /api/candidates` 可创建候选人
  - 新候选人自动生成 `rules-v2` 评分
  - `/candidates` 返回 200，页面包含“新建候选人”和“CSV 导入”
  - `/companies` 返回 200，页面包含“新建公司”

## 清理要求

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- Python `__pycache__`
- `.pytest_cache`

以上产物只用于阶段验收，不进入仓库。

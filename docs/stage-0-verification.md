# Stage 0 Verification

## Branch

- Current branch: `feature/stage-0`
- Based on existing completed demo branch: `feature/stage-8`
- Legacy old stage-0 branch preserved as: `feature/stage-0-legacy`

## Scope

Stage 0 is the baseline cleanup stage for the existing demo. It does not implement Stage 1+ product features.

Completed work:

- Backend text cleanup for core AI/demo services.
- Backend pytest database isolation through `backend/tests/conftest.py`.
- PRD gap review and technical documents updated.
- Stage task list updated to include Demo PRD P1 functions:
  - AI browser task real execution
  - Semi-automatic relationship graph
  - Manager view
- Frontend high-end visual baseline applied through global style tokens and interaction polish.
- Dependency/build artifacts are excluded from repository scope.

## Backend Verification

Command:

```powershell
cd backend
$py='C:\Users\HUAWEI\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -m pytest
```

Result:

```text
20 passed
```

Additional check:

```powershell
& $py -m compileall -q app scripts tests
```

Result:

```text
compileall_ok
```

## Frontend Verification

Stage 0 frontend work is limited to baseline visual polish and UTF-8 text cleanup.

Frontend build was not re-run in the final pass because `frontend/node_modules` was intentionally removed from the workspace to avoid keeping dependencies inside the project directory. To verify locally:

```powershell
cd frontend
npm.cmd install
npm.cmd run build
```

## Repository Cleanliness

Must not commit:

- `frontend/node_modules`
- `frontend/.next`
- `backend/talentnet.db`
- `__pycache__`
- `.pytest_cache`
- PDF/docx local product notes unless explicitly requested

## Frontend/Backend Boundary

Confirmed for Stage 0:

- Frontend does not call LLM directly.
- Frontend does not control Playwright directly.
- Frontend does not access the database.
- Backend owns AI, browser task, scoring, persistence and test isolation.

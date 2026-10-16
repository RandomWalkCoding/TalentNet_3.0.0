# Stage 8 Verification

Branch: `feature/stage-8`

## Scope

- Added backend logging setup.
- Added demo seed reset script:
  - `backend/scripts/reset_seed.py`
- Added frontend polish:
  - Mobile navigation.
  - Empty states.
  - Constrained main layout.
- Added demo walkthrough:
  - `docs/demo-walkthrough.md`
- Added one-command startup scripts:
  - `start.ps1`
  - `start.sh`

## Verification

Backend tests:

```bash
cd backend
python -m pytest
```

Result:

```text
20 passed
```

Frontend build:

```bash
cd frontend
npm run build
```

Result:

```text
Compiled successfully
```

Seed reset:

```bash
cd backend
python -m scripts.reset_seed
```

Result:

```text
TalentNet demo data reset complete.
```

Runtime smoke test:

```text
GET /api/health -> ok
GET /dashboard -> 200
GET /candidates/cand_lin_chen -> 200, renders AI insights panel
POST /api/candidates/cand_lin_chen/add-to-pool
POST /api/candidates/cand_lin_chen/generate-outreach
POST /api/feedback -> outcome in_process
GET /talent-pool -> 200
GET /analytics -> 200, renders feedback funnel
```

## One-command Demo

Windows PowerShell:

```powershell
.\start.ps1
```

macOS/Linux/Git Bash:

```bash
./start.sh
```

Then open:

```text
http://127.0.0.1:3000
```

## Notes

- Runtime smoke test used frontend port `3800` to avoid local port conflicts.
- Startup scripts default to frontend port `3000` and backend port `8000`.

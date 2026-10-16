# Stage 6 Verification

Branch: `feature/stage-6`

## Scope

- Added backend structured `LLMService`.
- Added Pydantic output schemas for:
  - AI summary.
  - Risk explanation.
  - Conflict notes.
  - Outreach variants.
- Added APIs:
  - `POST /api/candidates/{id}/generate-summary`
  - `POST /api/candidates/{id}/generate-outreach`
- Outputs cite saved evidence IDs.
- If no evidence exists, backend refuses deterministic generation.
- Added frontend AI insights panel on candidate detail page.
- Added editable outreach variants and copy button.

## Verification

Backend tests:

```bash
cd backend
python -m pytest
```

Result:

```text
18 passed
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

Runtime smoke test:

```text
POST /api/candidates/cand_lin_chen/generate-summary -> candidate cand_lin_chen, 2 cited evidence IDs
POST /api/candidates/cand_lin_chen/generate-outreach -> 3 variants, compliance note present
GET  /candidates/cand_lin_chen -> 200, renders AI insights panel and generate button
```

## Notes

- Stage 6 uses a local structured LLM service, not a frontend API key.
- The service is intentionally replaceable with OpenAI or a compatible LLM gateway in a later production hardening step.
- Frontend smoke test used port `3600` to avoid local port conflicts.

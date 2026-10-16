# Stage 12 PRD Alignment

## Added

- Document upload evidence ingestion
  - `POST /api/evidence/upload-document`
  - Supports txt, md, csv, pdf
  - Extracts text, creates evidence, optionally confirms and refreshes scoring
  - Candidate detail page now has an upload panel

- Semi-automatic organization graph
  - `GET /api/org-graph`
  - Builds company, department, candidate, and evidence nodes
  - Adds confidence-weighted edges
  - Frontend page: `/org-graph`

- Manager view
  - `GET /api/manager/summary`
  - Aggregates candidate, pool, feedback, conversion, and risk distribution metrics
  - Frontend page: `/manager`

## Verified

- Backend tests: 42 passed
- Frontend build: compiled successfully
- New version launched on:
  - Frontend: `http://127.0.0.1:3001`
  - Backend: `http://127.0.0.1:8001`

## Remaining Production Hardening

- Real auth and role-based access for manager pages
- Persistent document file storage instead of evidence-only text extraction
- True graph visualization library if deeper interaction is required
- Real provider/API integrations for LinkedIn, job boards, patents, and news

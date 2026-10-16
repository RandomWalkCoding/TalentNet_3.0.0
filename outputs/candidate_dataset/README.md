# TalentNet Candidate Dataset

This dataset contains 500 synthetic candidates for TalentNet product testing.

Files:

- `talentnet_candidates_500_import.csv`: upload this file through TalentNet's candidate CSV import flow.
- `talentnet_candidates_500_full.csv`: full labeled dataset with synthetic source signals, scores, priority, evidence summaries, and compliance notes.
- `talentnet_candidates_500_dataset.xlsx`: human-readable workbook with dashboard, import sheet, full dataset, and data dictionary.
- `dataset_summary.json`: compact generation summary and distribution counts.

Important compliance note:

The dataset is synthetic. It mimics Google/LinkedIn-style public search result signals, but it does not scrape Google or LinkedIn, does not use logged-in browser state, and does not contain real personal profile data.

Validation:

- Generated rows: 500
- Product CSV import API: passed
- Backend test suite: 38 passed

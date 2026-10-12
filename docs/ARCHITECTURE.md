# Architecture

```
┌────────────────────────────── Browser (Tailwind + vanilla JS) ──────────────────────────────┐
│ Landing · Auth · Dashboard · Profile · Resumes · Internships · Tracker (list/board) · Career AI │
└───────────────┬──────────────────────────────────────────────────────────────────────────────┘
                │ HTML pages + JSON APIs
┌───────────────▼──────────────────────────  Flask app (app.py)  ─────────────────────────────┐
│ auth.py (session)  │  profile / resume routes  │  /api/jobs/match  │  /api/m3/*  │  /api/applications │
└──┬────────────┬───────────────┬─────────────────────┬──────────────────────┬─────────────────┘
   │            │               │                     │                      │
   │   resume_service.py   matching_agent.py    skill_gap_agent.py     Application model
   │   resumeparser.py     ▲ rag_pipeline.py    application_agent.py   (tracker + reminders)
   │   profile_m1.py       │                    interview_agent.py
   │            │          │                    career_assistant.py
   ▼            ▼          ▼                     │
 SQLite   PDF (uploads/)  RAG index              ▼
 students, education,     rag_index/        llm_utils.call_json ──► OpenRouter (optional)
 experience, projects,    job_chunks.json          │
 skills, resumes,         job_embeddings.npy       └─► deterministic fallback on any failure
 career_*, applications   ▲
                          └── jobs_dataset.py (179 cleaned postings)
```

## Data flow
1. **Upload → profile.** PDF text (`pypdf`) → LLM extraction → normalised JSON → merged into the
   profile without overwriting manual edits (`profile_m1.merge_parsed_into_profile`).
2. **Profile → matches.** Profile → query text → RAG top-N chunks → per-job scoring
   (skills, education, experience, responsibilities, similarity) → ranked list with reasoning.
3. **Match → gap / tailoring / interview.** The selected job and the same profile go to the M3
   agents; the gap analysis feeds interview preparation.
4. **Anything → tracker.** "Track" on a match, or "Save to tracker" on generated material, creates or
   updates an `Application` row that stores the job description, letter and tailored resume.
5. **Tracker → reminders.** `application_stats_for` derives deadlines, interviews, follow-ups and
   pending applications that appear on the dashboard and the tracker.

## Design decisions
- **One LLM gateway** (`llm_utils.call_json`) with a mandatory deterministic fallback per agent.
- **Scores are computed, not generated**, so ranking is reproducible and testable.
- **Schema evolution** on SQLite is handled by `ensure_schema()` (ALTER TABLE ADD COLUMN) at start-up.
- **Tenant isolation:** every query filters by the session's `student_id`.

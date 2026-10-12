# AI Career Companion

Upload a resume, get ranked internships with an explained fit score, close skill gaps, tailor your
application, rehearse the interview and track every application to an offer.

## Run

```powershell
cd Companion
.\.venv\Scripts\python.exe app.py        # or: python -m venv .venv ; pip install -r requirements.txt
```

Open <http://127.0.0.1:8000>. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` and
`SECRET_KEY`. Without an API key every agent still works through its deterministic fallback.

Optional: `LLM_MAX_TOKENS` (cap per LLM call), `OPENROUTER_MODEL`.

## What is implemented (all four milestones)

| Milestone | Delivered | Code |
|---|---|---|
| **M1** Profile and resume understanding | accounts, structured profile CRUD, PDF upload, LLM parsing + merge, completion score | `app.py`, `models.py`, `resumeparser.py`, `resume_service.py`, `profile_m1.py` |
| **M2** Knowledge base and matching | 179 cleaned postings, 5-chunk RAG index, explainable weighted matcher, evaluation | `jobs_dataset.py`, `rag_pipeline.py`, `matching_agent.py`, `evaluate_m2.py` |
| **M3** Career agents | skill-gap analysis, resume/cover-letter tailoring (editable, refinable, downloadable), interview prep + mock-interview feedback, conversational assistant with saved history | `skill_gap_agent.py`, `application_agent.py`, `interview_agent.py`, `career_assistant.py`, `evaluate_m3.py` |
| **M4** Tracking, testing, optimisation, docs | tracker (list + drag-and-drop board, filters, reminders, follow-ups, interview outcomes, stored materials), 22 end-to-end tests, benchmark, report | `/api/applications*`, `tests/`, `evaluate_m4.py`, `docs/` |

## Test and evaluate

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v   # end-to-end suite (LLM disabled)
.\.venv\Scripts\python.exe evaluate_m2.py                      # retrieval / matching quality
.\.venv\Scripts\python.exe evaluate_m3.py                      # agent smoke checks
.\.venv\Scripts\python.exe evaluate_m4.py                      # latency / resource benchmark
.\.venv\Scripts\python.exe build_rag_index.py                  # rebuild the vector index
```

## Documentation

- [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) — final report (all required sections)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — diagram, data flow, design decisions

## Notes

- The internship dataset is synthetic, written for development and evaluation.
- Existing SQLite databases are upgraded automatically at start-up (`ensure_schema`).
- Passwords are hashed; all data access is scoped to the logged-in student; uploads are UUID-named PDFs (5 MB limit).

## LLM configuration & offline mode
Set `GEMINI_API_KEY` (or `OPENROUTER_API_KEY`) in `.env`; Gemini takes priority. Without a key, every feature still works: resume parsing uses the offline parser in `heuristic_parser.py`, and matching, gap analysis, tailoring, interview scoring and the assistant use deterministic fallbacks.

## Extras
- `python seed_demo.py` creates the demo account (`demo@example.com` / `Demo@12345`) with a parsed resume and sample applications.
- `python evaluate_m1.py` measures offline extraction coverage on the sample resumes.
- Settings page (account, password, JSON export, delete account), command palette (Ctrl/Cmd+K), reminders bell.
- See `docs/DEMO_SCRIPT.md` for a guided walkthrough.

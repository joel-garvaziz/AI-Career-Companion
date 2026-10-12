# AI Career Companion Agent for Internship Matching and Interview Preparation
### Final project report

## 1. Introduction
Students applying for internships juggle resumes, scattered postings, unclear requirements and
missed deadlines. **AI Career Companion** is a web application that turns a single uploaded resume
into a structured profile, retrieves and ranks relevant internships with an explained compatibility
score, identifies skill gaps, produces tailored application material, prepares the student for
interviews, and tracks every application through to an outcome.

## 2. Problem statement
- Job postings are unstructured and hard to compare against one's real background.
- Generic AI writing tools invent skills and experience, which is harmful in applications.
- Students lose applications to missed deadlines and forgotten follow-ups.

## 3. Objectives
1. Parse resumes into a structured candidate profile (M1).
2. Build a curated internship knowledge base and a RAG retrieval pipeline (M2).
3. Score and rank matches with transparent reasoning (M2).
4. Provide skill-gap analysis, application tailoring, interview preparation and a conversational
   assistant, all grounded in real profile data (M3).
5. Track applications, deadlines, interviews and follow-ups (M4).
6. Validate, optimise and document the system (M4).

## 4. System requirements
| Area | Requirement |
|---|---|
| Runtime | Python 3.10+ (tested on 3.10), Windows/Linux/macOS |
| Backend | Flask 3, Flask-SQLAlchemy, SQLite |
| AI | `sentence-transformers` (all-MiniLM-L6-v2) for embeddings; OpenRouter chat model (optional) |
| Browser | Any modern browser; UI is Tailwind (CDN) with vanilla JS |
| Resources | ~1.6 MB vector index; embedding model download ~90 MB on first run |

## 5. System architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for the diagram and data flow. Summary: browser UI → Flask
API layer → SQLite (profiles, resumes, conversations, applications) and the RAG index; agents call an
LLM through a single helper (`llm_utils.py`) and always have a deterministic fallback.

## 6. Dataset and knowledge base
- **Size:** 179 postings after cleaning (180 authored; one exact duplicate removed).
- **Categories (10 domains):** Python Backend, Data Analyst, Machine Learning, Frontend, Full Stack,
  Cloud/DevOps, Cybersecurity, Flutter, SQL/Database, AI/NLP (17–18 each). Two locations (Bengaluru, Chennai).
- **Source:** curated *synthetic* benchmark data written for this project (not scraped) — declared in
  every record's `source` field.
- **Schema:** job id, title, company, location, type, duration, description, responsibilities,
  required skills, preferred skills, qualifications, education and experience requirements, domain.
- **Preprocessing (`jobs_dataset._clean_dataset`):** whitespace/case-insensitive de-duplication of
  skill lists, preferred skills that repeat a required skill are dropped, records missing mandatory
  fields are rejected, exact-duplicate postings are removed. Tested in `tests/test_e2e.py`.

## 7. RAG pipeline
- **Chunking:** each posting → 5 semantic chunks (overview, responsibilities, required skills,
  preferred skills, qualifications) = 895 chunks. Section-level chunks keep each vector focused on one
  kind of evidence and let the matcher see which part of a posting matched.
- **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), L2-normalised.
- **Index:** NumPy matrix (`rag_index/job_embeddings.npy`) + chunk metadata JSON; cosine similarity
  is a single matrix product. At 895 vectors an ANN library would add complexity without benefit.
- **Retrieval:** query → top-N chunks → grouped per job → best-chunk similarity feeds the matcher.

## 8. Multi-agent architecture
Agents share one profile schema and one job schema, so outputs of one agent are valid inputs of the next.

| Agent | Module | Input | Output |
|---|---|---|---|
| Resume parser | `resumeparser.py`, `resume_service.py` | PDF text | structured profile JSON |
| Job-Resume Matching | `matching_agent.py` | profile (+ optional query) | ranked jobs, score, breakdown, reasoning |
| Skill Gap | `skill_gap_agent.py` | profile, job | critical / partial / preferred / experience / qualification gaps + recommendations |
| Application Customisation | `application_agent.py` | profile, job | tailored resume emphasis, cover letter, integrity warnings |
| Interview Preparation | `interview_agent.py` | profile, job, gaps | typed questions, guidance, revision topics; mock-answer evaluation |
| Career Assistant | `career_assistant.py` | message, history, tool outputs | grounded answer, persisted conversation |

## 9. Agent design and implementation
- **Deterministic core, LLM on top.** Scores and gap classification are rule-based and reproducible;
  the LLM only writes explanations/prose. If the API is missing, out of credit or returns invalid
  JSON, `llm_utils.call_json` returns the agent's deterministic fallback, so the product never breaks.
- **Matching score** = weighted sum: required skills 40 %, preferred 15 %, education 15 %,
  experience 10 %, responsibilities overlap 10 %, retrieval similarity 10 %. Alias-aware skill matching.
- **Grounding.** Prompts forbid invented skills, metrics or employers; the tailoring agent reports
  `keywords_used` vs `keywords_not_supported`, and refinement requests re-apply the same rule.
- **Human in the loop.** Generated resume and cover letter are editable, refinable by instruction,
  downloadable and saveable to the tracker.
- **Mock interview.** Answers are evaluated by the LLM when available, otherwise by a transparent
  heuristic (depth + coverage of the role's required skills) that returns strengths and improvements.
- **Assistant.** Intent routing selects which agents to run as tools, their JSON output is passed as
  evidence, and the last 8 messages of the persisted conversation supply context.

## 10. Application tracking module
- **Data:** company, title, description, location, URL, status (10 stages), application date,
  deadline, interview date + status + notes/outcome, follow-up date + action, free notes, linked resume,
  tailored resume text and cover letter.
- **Operations:** create (manual or one click from a match), edit, drag-and-drop status change on a
  board view, quick status change, delete, search and filter by company, role, status, group
  (active/completed), deadline range and application-date range, sort by several fields.
- **Reminders / dashboard:** upcoming deadlines (14 days), scheduled interviews, follow-ups due,
  pending applications (applied/under review with no update for 7 days), plus totals for tracked,
  active, completed, interviews, offers and rejected.
- **Isolation:** every query filters by `student_id`; covered by a cross-user test.

## 11. Testing and evaluation
**Automated end-to-end suite** — `python -m unittest discover -s tests` — 22 tests, all passing:
dataset schema/cleaning, retrieval relevance, matching ranking and determinism, gap classification,
"no invented skills", interview question coverage, mock-answer scoring, full HTTP workflow (register →
profile → matching → gap → tailoring → interview → assistant with context retention → tracker CRUD,
filters, reminders), authorisation, and page rendering.

**Retrieval / matching evaluation** (`evaluate_m2.py`, 5 synthetic student profiles, LLM off):

| Metric | Result |
|---|---|
| Retrieval Hit@5 | 100 % |
| Mean Reciprocal Rank | 1.000 |
| Matching Hit@5 | 100 % |
| Score std-dev (spread) | 3.5 |

**Agent workflow check** (`evaluate_m3.py`): skill-gap, tailoring, interview and orchestration
smoke tests pass.

## 12. Optimisation and performance (`evaluate_m4.py`, CPU only, LLM off)
| Measure | Result |
|---|---|
| Cold start (load model + index) | 3.6 s |
| Retrieval, top-5 | ≈ 20 ms / query |
| Ranked matching of 10 jobs | ≈ 41 ms |
| Skill gap / tailoring / interview prep (deterministic) | < 1 ms each |
| Prompt size for one agent call | ≈ 2.4 k chars ≈ 600 tokens |
| Index size on disk | 1.63 MB |

Optimisations applied: section-level chunking; one-matrix cosine search; deterministic scoring so
only prose needs LLM tokens; bounded context (8 messages, 35 k-char tool context); matching sorts once
(a bug that re-sorted per iteration was fixed); every LLM call caps  (default 1200–3000, ) — the previous unbounded default requested 16 k tokens and failed on low-credit accounts; every LLM call now caps `max_tokens` (1200–3000, configurable via `LLM_MAX_TOKENS`) — the previous unbounded default requested 16 k tokens and failed on low-credit accounts; LLM failures are logged and degrade to fallbacks
instead of surfacing raw API errors to users.

## 13. Results and analysis
The system completes the full student workflow end to end. Retrieval and matching place the correct
domain in the top five for every evaluated profile. Explanations are grounded in profile data, and
all agents remain usable without an LLM.

## 14. Limitations
- The dataset is synthetic; several postings in a domain share identical requirements, so scores tie
  (e.g. many 78.69). Real postings would separate them.
- Only PDF resumes are supported; parsing runs inside the request (a worker queue would be needed at scale).
- Evaluation uses 5 synthetic profiles and domain-level relevance labels; it is a benchmark, not a
  statistically robust study. LLM-quality metrics (relevance, personalisation) were judged manually,
  not measured automatically.
- Sessions use a single shared secret and there is no CSRF token or rate limiting (acceptable for a
  course project, not for production).
- Reminders are shown in-app; there is no e-mail/push delivery.

## 15. Future scope
Live job ingestion and de-duplication; ANN index and hybrid (BM25 + dense) retrieval; background
workers; e-mail/calendar reminders; resume PDF export in the tailored layout; automated LLM-as-judge
evaluation; multi-user hardening (CSRF, rate limits, password reset).

## 16. Conclusion
All four milestones are implemented: profile and resume understanding, a RAG-based job knowledge
base with an explainable matcher, four downstream career agents, and a full application-tracking
module — verified by an automated suite and documented here.

## Addendum: Final Hardening

- **Offline resume parser (M1):** `heuristic_parser.py` extracts contact details, skills (section parsing plus a vocabulary scan), education, experience and projects without an LLM. `resume_service.parse_resume` tries the LLM (Gemini or OpenRouter) first and falls back automatically; the result records which parser was used. `evaluate_m1.py` reports 100% field coverage (9/9 fields) on both distinct sample resumes.
- **Provider flexibility:** `llm_utils.llm_config()` selects Gemini (OpenAI-compatible endpoint) or OpenRouter from the environment; all agents share it.
- **Product UI:** sidebar application shell, dashboard onboarding checklist, command palette, reminders bell, settings page (export/delete data), and 404/500 pages.
- **Testing:** 27 automated tests, including offline parser, settings and error-page tests.
- **Demo:** `seed_demo.py` and `docs/DEMO_SCRIPT.md`.

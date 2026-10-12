# AI Career Companion — Agile Project Documentation

## 1. Document Control

| Field | Details |
|---|---|
| Project | AI Career Companion Agent for Internship Matching and Interview Preparation |
| Project start | 19 August 2026 |
| Methodology | Agile, milestone-based; each milestone planned for 2 weeks |
| Status date | 12 October 2026 |
| Current status | Ongoing; Milestone 4 completion is not yet verified |
| Version | 0.2 — Concise working document |
| Source | `Project Details.txt` |
| Document owner | TBD |

**Status definitions:** Planned = not started or not evidenced; In progress = work started but not accepted; Completed = acceptance criteria met with evidence; Blocked = impediment prevents progress; Unverified = status evidence unavailable.

> Important: The dates below are the original plan, not proof that work was completed. Update statuses using repository evidence, test results, commits, or review records.

## 2. Project Overview

### Problem
Students applying for internships often need separate tools to find suitable roles, understand skill gaps, tailor application materials, prepare for interviews, and track applications.

### Objective
Build an AI-powered web application that uses student profiles, resume parsing, a curated internship knowledge base, Retrieval-Augmented Generation (RAG), and specialised agents to support the internship application process.

### Scope
- Student profile creation and resume upload/parsing
- Internship dataset and semantic retrieval using RAG
- Job-resume matching with scores, ranking, and explanations
- Skill-gap analysis
- Resume and cover-letter customization
- Interview preparation and conversational career guidance
- Application tracking
- End-to-end testing, optimization, technical documentation, and demonstration

### Key constraint
Milestone 1 deliverables (GitHub repository link, system architecture, and technology stack) had a source-specified submission deadline of **28 August 2026**. Whether this submission occurred is not recorded here.

## 3. Milestone Plan

Milestones are planned as inclusive 14-calendar-day periods, starting 19 August 2026.

| Milestone | Planned dates | Focus | Main deliverables | Status as of 12 Oct 2026 |
|---|---|---|---|---|
| M1 | 19 Aug–1 Sep 2026 | Foundation and candidate understanding | Research, architecture, agent roles, profile module, resume upload and parsing | Completion to be confirmed; planned end passed |
| M2 | 2–15 Sep 2026 | Internship knowledge and matching | 150–200 curated postings, RAG pipeline, matching agent, evaluation | Completion to be confirmed; planned end passed |
| M3 | 16–29 Sep 2026 | Skill gaps and career agents | Skill-gap agent, resume/cover-letter customization, interview agent, conversational assistant | Completion to be confirmed; planned end passed |
| M4 | 30 Sep–13 Oct 2026 | Tracking, testing, optimization, documentation | Application tracker, test results, optimization evidence, report, final demo | Ongoing; completion not verified |

**Total planned duration:** 8 weeks (19 August–13 October 2026). Do not mark a milestone complete solely because its planned end date has passed.

## 4. Milestone Work Breakdown

### M1 — Foundation and Candidate Understanding
- **M1.1 Research:** Study internship workflows, RAG, and multi-agent design; document technology choices.
- **M1.2 Architecture:** Define architecture, agent responsibilities, student profile schema, and resume-to-profile data flow.
- **M1.3 Profile module:** Create student profiles, upload resumes, and store profile/resume metadata.
- **M1.4 Resume parsing:** Extract skills, education, experience, and projects; store structured output and test sample resumes.

### M2 — Internship Knowledge and Job-Resume Matching
- **M2.1 Dataset:** Curate and clean 150–200 postings using a consistent schema.
- **M2.2 RAG:** Chunk postings, generate embeddings, build a vector index, and implement semantic search.
- **M2.3 Matching agent:** Compare candidate profile with job requirements; return compatibility scores, explanations, and ranked roles.
- **M2.4 Evaluation:** Test retrieval and rankings with varied sample profiles and manually expected results.

### M3 — Skill Gap, Application Customization, and Interview Preparation
- **M3.1 Skill-gap agent:** Classify missing/partial skills and qualification or experience gaps; provide recommendations.
- **M3.2 Resume and cover-letter agent:** Generate role-specific materials grounded in the candidate’s actual profile; do not invent achievements or experience.
- **M3.3 Interview agent:** Generate technical, resume-based, project-based, role-specific, and HR questions with preparation guidance. Mock interviews are optional.
- **M3.4 Conversational assistant:** Integrate agent and RAG outputs to provide personalized career guidance and support follow-up questions.

### M4 — Tracking, Testing, Optimization, and Documentation
- **M4.1 Application tracker:** Manage applications, statuses, deadlines, interview details, notes, search/filtering, and dashboard summaries. Reminders are conditional on implementation.
- **M4.2 End-to-end testing:** Test the complete workflow, RAG relevance, agent integration, grounding, and conversational context.
- **M4.3 Optimization:** Improve retrieval, prompts, matching logic, and response performance using recorded before/after measurements.
- **M4.4 Documentation and demo:** Complete technical documentation, project report, and end-to-end demonstration.

## 5. Agile Working Approach

Each milestone represents a planned two-week iteration. Divide the work into weekly tasks, review progress regularly, and record actual outcomes.

### Required sprint records
For each milestone, record:
1. **Sprint goal** — the outcome intended by the end of the two weeks.
2. **Tasks and owners** — task ID, assignee, dependency, status, and due date.
3. **Acceptance criteria** — conditions that demonstrate the feature works.
4. **Sprint review** — what was demonstrated, what was accepted, feedback, and evidence links.
5. **Retrospective** — what went well, what did not, and improvement actions.

Historical reviews and retrospectives are not supplied; enter them only when records are available.

### Definition of Done
A task can be marked complete when:
- Its acceptance criteria are met.
- Relevant tests have been executed and results recorded.
- Code and documentation are updated.
- No secrets or private data are committed.
- The result has evidence, such as a commit, test report, screenshot, or demo record.

## 6. Core Acceptance Criteria

| ID | Acceptance criteria |
|---|---|
| M1 | A student can create a profile and upload a resume; structured resume details are extracted and stored. |
| M2 | A cleaned dataset of 150–200 postings is available; semantic retrieval returns relevant roles; matching produces ranked results, scores, and grounded explanations. |
| M3 | Skill gaps have actionable recommendations; tailored application materials do not invent candidate facts; interview preparation and conversational guidance use profile/job context. |
| M4 | Applications can be tracked and filtered; the end-to-end workflow is tested; optimizations have before/after evidence where measured; documentation and demo are prepared. |

Any numeric quality thresholds should be agreed by the project team before being treated as requirements.

## 7. Testing and Evaluation

Record actual outcomes; do not report a test as passed unless it was executed.

| Area | What to verify | Evidence |
|---|---|---|
| Resume parsing | Skills, education, experience, and projects extracted correctly | Sample resumes and expected-vs-actual results |
| Dataset | 150–200 valid postings; duplicates/incomplete records removed | Dataset and record count |
| RAG | Relevant postings appear in Top-K results | Query set and retrieval results |
| Matching | Ranking, score consistency, and explanations are reasonable and grounded | Sample profiles and evaluation sheet |
| Career agents | Gap analysis, tailored materials, and interview questions are relevant | Sample outputs and review checklist |
| Grounding | Generated materials do not invent skills, experience, or achievements | Claim review against profile |
| Conversation | Follow-up questions use the correct prior context | Test dialogue transcripts |
| Application tracker | Status, dates, notes, filters, and dashboard counts are correct | Test cases and screenshots |
| End-to-end | Profile → resume parsing → retrieval → matching → skill gap → customization → interview preparation → tracking | Execution log |
| Security | Secrets excluded; uploaded resume data handled appropriately | Security checklist |

### Test case template

| ID | Requirement | Steps / preconditions | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|---|
| TC-001 | TBD | TBD | TBD | Not recorded | Not executed | TBD |

## 8. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Poor resume extraction | Validate output schema and test varied resume layouts. |
| Irrelevant RAG results | Evaluate retrieval on a judged query set and tune chunking/embedding/retrieval settings. |
| Incorrect match scores | Document scoring criteria and compare results with manually expected rankings. |
| Unsupported generated claims | Ground outputs in profile/job data and review generated materials. |
| Agent integration failures | Define clear input/output contracts and add integration tests. |
| API limits or service failures | Handle errors, apply backoff where appropriate, and cache reusable results when suitable. |
| Exposure of secrets or resume data | Use environment variables, ignore secret files, and avoid committing personal data. |
| Schedule slippage | Prioritize must-have requirements, record blockers, and approve changes to planned dates. |
| Insufficient evaluation evidence | Maintain representative test profiles, queries, expected outputs, and execution logs. |

Assign a risk owner and current status when known; otherwise use **TBD**.

## 9. Current Status Report — 12 October 2026

Based on the supplied project requirements alone, implementation status cannot be independently verified.

- **M1:** Planned end passed; completion status to be confirmed.
- **M2:** Planned end passed; completion status to be confirmed.
- **M3:** Planned end passed; completion status to be confirmed.
- **M4:** Current planned milestone; completion not verified.
- **Testing results:** Not supplied.
- **Dataset count:** Not confirmed.
- **Actual team members, task owners, blockers, and sprint review records:** Not supplied.

### Immediate next actions
1. Verify each milestone against the repository and mark items as completed, in progress, blocked, or unverified.
2. Confirm the dataset count and record RAG/matching evaluation results.
3. Run and record end-to-end tests.
4. Review secret handling and privacy protections.
5. Update documentation to match the actual implementation.
6. Complete and rehearse the end-to-end demonstration.
7. If work extends beyond 13 October, record an approved schedule change and revised forecast.

## 10. Lightweight Tracking Templates

### Weekly progress update
- **Week / dates:**
- **Planned work:**
- **Completed work and evidence:**
- **Work in progress:**
- **Blockers / risks:**
- **Next actions:**

### Decision log
| ID | Date | Decision | Reason | Owner | Status |
|---|---|---|---|---|---|
| D-001 | TBD | TBD | TBD | TBD | Open |

### Change request
| Field | Entry |
|---|---|
| Request ID / date | TBD |
| Requested change and reason | TBD |
| Scope/schedule/quality impact | TBD |
| Decision and approver | TBD |
| Revised date, if approved | TBD |

## 11. Final Demonstration Checklist

- [ ] Create or open a student profile.
- [ ] Upload a sample resume and show extracted profile details.
- [ ] Search the internship knowledge base.
- [ ] Show ranked internship matches and explanations.
- [ ] Show skill-gap recommendations.
- [ ] Generate and review a tailored resume and cover letter.
- [ ] Generate interview questions and preparation guidance.
- [ ] Ask follow-up questions in the conversational assistant.
- [ ] Add an internship to the application tracker and update its status.
- [ ] Show test results, known limitations, and relevant documentation.

Mark each item complete only after it has been demonstrated.

## 12. Document Maintenance

Update this document after each sprint review. Record changes to scope, actual dates, status, decisions, risks, test results, and evidence links. Keep planned dates separate from actual results.

### Open questions
- Who owns the project and each workstream?
- What are the confirmed technology stack and deployment details?
- Is the 150–200 posting dataset complete, and what is its verified record count?
- Which milestones and acceptance criteria have been demonstrated?
- What test results, blockers, and review records are available?
- Has the team approved measurable quality thresholds?

### Changelog
| Version | Date | Change |
|---|---|---|
| 0.2 | 12 October 2026 | Condensed the Agile documentation to core project, milestone, acceptance, testing, risk, status, and tracking information. |

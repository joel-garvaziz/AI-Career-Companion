# AI Career Companion

AI Career Companion is a Flask-based career-support application that helps students move from resume analysis to internship matching, application preparation, interview practice, and application tracking.

## Features

- **Profile and resume analysis (M1):** Create an account, manage a structured student profile, upload a PDF resume, extract resume details, and view profile-completion progress.
- **Internship discovery and matching (M2):** Search a development dataset of internship postings, retrieve relevant opportunities, and receive ranked matches with explainable fit scores.
- **Career assistance (M3):** Identify skill gaps, tailor resumes and cover letters, prepare for interviews, receive mock-interview feedback, and use a conversational career assistant.
- **Application tracking (M4):** Track application status, organise applications in a list or board, record interview outcomes, and manage reminders and follow-ups.
- **Fallback mode:** Core features can use deterministic/offline fallbacks when an LLM API key is not configured.
- **Security-conscious defaults:** Password hashing, user-scoped data access, UUID-named PDF uploads, and a 5 MB upload limit.

## Technology

- Python and Flask
- SQLite for local application data
- HTML, CSS, and JavaScript templates
- Resume parsing and retrieval-augmented generation (RAG)
- Optional LLM integration through configured providers
- Python `unittest` test suite

## Requirements

- Python 3.10 or newer recommended
- `pip`
- An LLM API key only if you want provider-backed responses; fallback behaviour is available without one

## Setup on Windows (PowerShell)

1. Open a terminal in the project directory.
2. Create and activate a virtual environment if you do not already have one:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Create a local environment file from the example, if the example file is available:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Edit `.env` and add your own secret key and optional provider key. Never commit `.env` or real credentials to Git.
6. Start the application:

   ```powershell
   python app.py
   ```

7. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

If you already have a working `.venv`, you can run the app with `\.venv\Scripts\python.exe app.py` without activating it first.

## Environment configuration

Keep environment-specific values in `.env`, which should remain untracked by Git. Common settings include:

- `SECRET_KEY` — secret used by Flask sessions; set a strong, private value.
- `OPENROUTER_API_KEY` — optional key for OpenRouter-backed model calls.
- `GEMINI_API_KEY` — optional key for Gemini-backed model calls, if supported by your current configuration.
- `OPENROUTER_MODEL` — optional model selection for OpenRouter.
- `LLM_MAX_TOKENS` — optional limit on generated tokens per model call.

Use only the variables supported by your current application configuration. `.env.example` should contain placeholders, not real secrets. If a key is absent, supported features fall back to their offline/deterministic implementations.

## Run tests and evaluation scripts

Run these commands from the project root:

```powershell
python -m unittest discover -s tests -v
python evaluate_m1.py
python evaluate_m2.py
python evaluate_m3.py
python evaluate_m4.py
```

Rebuild the retrieval index when needed:

```powershell
python build_rag_index.py
```

Use the project's virtual-environment Python executable if your environment is not activated, for example `\.venv\Scripts\python.exe -m unittest discover -s tests -v`.

## Project structure

```text
.
├── app.py                  # Flask application entry point
├── auth.py                 # Authentication helpers
├── models.py               # Application data models
├── resumeparser.py         # Resume parsing
├── resume_service.py       # Resume-related services
├── rag_pipeline.py         # Retrieval and RAG pipeline
├── matching_agent.py       # Internship matching
├── skill_gap_agent.py      # Skill-gap analysis
├── application_agent.py    # Resume and cover-letter tailoring
├── interview_agent.py      # Interview preparation and feedback
├── career_assistant.py     # Conversational career assistant
├── templates/              # HTML templates
├── tests/                  # Automated tests
├── docs/                   # Project and architecture documentation
├── requirements.txt        # Python dependencies
└── .env.example            # Environment-variable template (placeholders only)
```

## Documentation

- [Project report](docs/PROJECT_REPORT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Demo walkthrough](docs/DEMO_SCRIPT.md)

## Demo data and notes

- The internship dataset is synthetic and intended for development and evaluation.
- `python seed_demo.py` creates a demo account and sample application data. Use this only in a local/demo environment and change or remove demo credentials before any public deployment.
- Existing SQLite databases may be upgraded automatically by the application at startup.
- Do not upload real resumes, local databases, API keys, passwords, `.env` files, or virtual environments to a public repository.

## Contributing / development workflow

1. Create a feature branch before making larger changes.
2. Keep secrets and generated files out of Git.
3. Run the relevant tests and evaluation scripts.
4. Review `git status` before committing.

## Disclaimer

AI-generated recommendations and match scores are decision-support aids, not guarantees of internship eligibility or hiring outcomes. Review generated application materials before using them.

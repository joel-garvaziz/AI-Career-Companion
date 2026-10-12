# Demo Script (about 5 minutes)

Setup: `python seed_demo.py`, then `python app.py` and open http://localhost:8000. Log in as `demo@example.com` / `Demo@12345`.

1. **Home** - the "Your next step" card guides new users; below it are applications, interviews, offers and what is coming up.
2. **My resumes** (avatar menu) - upload a PDF. Your profile is filled in automatically; the result page shows the skills found and what to do next.
3. **Profile** - tabs for Basics, Skills, Education, Experience and Projects. Edit anything; the completion bar updates.
4. **Internships** - the list is ranked for you. Use the search box (and Filters) to narrow it down. "See the full picture" shows skills and details. "Save to my applications" adds it to the tracker; "Get advice for this role" opens the coach.
5. **Career coach** - choose a role, then use "What am I missing?", "Resume & cover letter" or "Interview prep" (with mock-interview scoring). The "Ask a question" tab is a chat assistant that knows your profile.
6. **Applications** - add an application, switch between List and Board (drag cards between columns), use More for date filters, and open a card for interview notes and follow-ups.
7. **Settings** - change your name, email or password, download your data, or delete your account.

Tip: press Ctrl/Cmd+K anywhere to search pages and internships.

Evaluation commands: `python evaluate_m1.py`, `evaluate_m2.py`, `evaluate_m3.py`, `evaluate_m4.py`, `python -m unittest discover -s tests`.

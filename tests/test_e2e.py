"""End-to-end tests (M4.2): profile -> resume -> retrieval -> matching -> skill gap
-> tailoring -> interview prep -> assistant -> application tracking.

Run from the project root:   python -m unittest discover -s tests -v

The LLM is disabled (empty API key) so every agent runs its deterministic path;
this keeps the suite fast, free and reproducible.
"""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_tmp) / "test.db").replace("\\", "/")
os.environ["OPENROUTER_API_KEY"] = ""; os.environ["GEMINI_API_KEY"] = ""; os.environ["GOOGLE_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret"

from app import app  # noqa: E402
from database import db  # noqa: E402
from models import Application, Student  # noqa: E402
import jobs_dataset  # noqa: E402
from rag_pipeline import semantic_search  # noqa: E402
from matching_agent import match_profile  # noqa: E402
from skill_gap_agent import analyze  # noqa: E402
from application_agent import customize  # noqa: E402
from interview_agent import prepare, evaluate_answer  # noqa: E402
from profile_m1 import merge_parsed_into_profile, completion_score  # noqa: E402

app.config["TESTING"] = True

PROFILE = {
    "full_name": "Test Student",
    "skills": ["Python", "Flask", "SQL", "Git", "Communication"],
    "education": [{"degree": "B.Tech", "field_of_study": "Computer Science"}],
    "experience": [],
    "projects": [{"project_name": "Task API", "description": "REST API built with Flask and SQL.", "technologies": ["Flask", "SQL"]}],
}


class DatasetTests(unittest.TestCase):
    def test_size_and_schema(self):
        jobs = jobs_dataset.get_all_jobs()
        self.assertTrue(150 <= len(jobs) <= 200)
        for field in jobs_dataset.REQUIRED_FIELDS:
            self.assertTrue(all(j.get(field) for j in jobs), field)

    def test_cleaning_removes_duplicate_skills(self):
        for job in jobs_dataset.get_all_jobs():
            for key in ("required_skills", "preferred_skills"):
                lowered = [s.lower() for s in job[key]]
                self.assertEqual(len(lowered), len(set(lowered)))

    def test_unique_ids(self):
        ids = [j["job_id"] for j in jobs_dataset.get_all_jobs()]
        self.assertEqual(len(ids), len(set(ids)))


class OfflineParserTests(unittest.TestCase):
    TEXT = (
        "Asha Rao\nasha@example.com | +91 98765 43210\nlinkedin.com/in/asha | github.com/asha\n"
        "EDUCATION\nXYZ University 2021-2025\nB.Tech Computer Science CGPA: 8.1 / 10\n"
        "SKILLS\nLanguages: Python, SQL\nFrameworks: Flask\nTools: Git, Docker\n"
        "PROJECTS\nJob Tracker Jan 2025\nPython, Flask, SQLite\n• Built a tracker for applications.\n"
        "EXPERIENCE\nAcme Corp June 2024\nSoftware Intern\n• Wrote APIs.\n"
    )

    def test_extracts_core_fields(self):
        from heuristic_parser import heuristic_parse
        d = heuristic_parse(self.TEXT)
        self.assertEqual(d["full_name"], "Asha Rao")
        self.assertEqual(d["email"], "asha@example.com")
        self.assertIn("Python", d["technical_skills"])
        self.assertIn("Docker", d["tools"])
        self.assertEqual(d["projects"][0]["project_name"], "Job Tracker")
        self.assertIn("Flask", d["projects"][0]["technologies"])
        self.assertEqual(d["experience"][0]["company"], "Acme Corp")
        self.assertTrue(d["education"])

    def test_parse_resume_falls_back_offline(self):
        from unittest import mock
        import resume_service
        with mock.patch.object(resume_service, "extract_pdf_text", return_value=self.TEXT):
            d = resume_service.parse_resume("ignored.pdf")
        self.assertEqual(d["parser"], "offline")
        self.assertEqual(d["email"], "asha@example.com")


class RagTests(unittest.TestCase):
    def test_semantic_search_relevance(self):
        results = semantic_search("python flask backend api developer", top_k=5)
        self.assertEqual(len(results), 5)
        text = " ".join(str(r) for r in results).lower()
        self.assertIn("python", text)

    def test_irrelevant_query_scores_lower_than_relevant(self):
        good = semantic_search("machine learning pytorch model training", top_k=1)[0]
        bad = semantic_search("underwater basket weaving", top_k=1)[0]
        score = lambda r: r.get("score", r.get("similarity", 0))
        self.assertGreater(score(good), score(bad))


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.job = jobs_dataset.get_job("INT-001")

    def test_matching_scores_and_ranks(self):
        results = match_profile(PROFILE, top_k_retrieval=20, top_k_results=10, include_llm_reasoning=False)
        self.assertTrue(results)
        scores = [r["score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0 <= s <= 100 for s in scores))
        self.assertIn("score_breakdown", results[0])

    def test_matching_is_consistent(self):
        a = match_profile(PROFILE, include_llm_reasoning=False)
        b = match_profile(PROFILE, include_llm_reasoning=False)
        self.assertEqual([r["job"]["job_id"] for r in a], [r["job"]["job_id"] for r in b])

    def test_skill_gap_classification(self):
        profile = {"skills": [{"name": "Python"}, {"name": "Flask"}]}
        result = analyze(profile, self.job)
        missing = [g.get("skill") for g in result["critical_missing_skills"]]
        self.assertIn("SQL", missing)
        self.assertNotIn("Python", missing)

    def test_application_does_not_invent_skills(self):
        profile = {"full_name": "T", "skills": [{"name": "Python"}], "projects": []}
        out = customize(profile, self.job)
        self.assertEqual(out["resume"]["priority_skills"], ["Python"])
        self.assertIn("Dear Hiring Team", out["cover_letter"])

    def test_interview_questions_cover_types(self):
        gap = analyze({"skills": [{"name": "Python"}]}, self.job)
        plan = prepare({"skills": [{"name": "Python"}], "projects": []}, self.job, gap)
        kinds = {q["type"] for q in plan["questions"]}
        self.assertTrue({"technical", "HR/general"} <= kinds)

    def test_mock_interview_feedback(self):
        weak = evaluate_answer("Describe a project.", "I built stuff.", {}, self.job)
        strong = evaluate_answer(
            "Describe a project.",
            "I built a REST API with Python, Flask and SQL for task management. " * 6,
            {}, self.job,
        )
        self.assertGreater(strong["score"], weak["score"])
        self.assertTrue(strong["improvements"])


class WebFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with app.app_context():
            db.create_all()

    def setUp(self):
        self.client = app.test_client()
        self.email = f"user{os.urandom(3).hex()}@example.com"
        r = self.client.post("/register", data={"full_name": "Flow Tester", "email": self.email, "password": "Password123", "confirm_password": "Password123"})
        self.assertEqual(r.status_code, 302)

    def test_auth_required(self):
        anon = app.test_client()
        self.assertEqual(anon.get("/dashboard").status_code, 302)
        self.assertEqual(anon.get("/api/applications").status_code, 302)

    def test_bad_login_rejected(self):
        c = app.test_client()
        r = c.post("/login", data={"email": self.email, "password": "wrong"})
        self.assertIn(b"Invalid email or password", r.data)

    def test_profile_and_completion(self):
        self.client.post("/profile/skill", data={"name": "Python", "category": "technical"})
        self.client.post("/profile/education", data={"degree": "B.Tech", "institution": "XYZ"})
        data = self.client.get("/api/profile").get_json()
        self.assertEqual([s["name"] for s in data["skills"]], ["Python"])
        self.assertGreater(data["completion"], 0)

    def test_resume_merge_populates_profile(self):
        with app.app_context():
            student = Student.query.filter_by(email=self.email).first()
            merge_parsed_into_profile(student, {"technical_skills": ["Python", "SQL"], "education": [{"degree": "B.Tech", "institution": "XYZ"}], "projects": [{"project_name": "P1"}]})
            db.session.refresh(student)
            self.assertEqual({s.name for s in student.skills}, {"Python", "SQL"})
            self.assertGreater(completion_score(student), 0)

    def test_reparsing_same_resume_does_not_duplicate(self):
        parsed = {"technical_skills": ["Python", "SQL"], "programming_languages": ["python"], "tools": ["Git"],
                  "education": [{"degree": "B.Tech", "institution": "XYZ"}], "projects": [{"project_name": "P1"}],
                  "experience": [{"company": "Acme", "job_title": "Intern"}]}
        with app.app_context():
            student = Student.query.filter_by(email=self.email).first()
            for _ in range(3):
                merge_parsed_into_profile(student, parsed)
                db.session.commit()
            db.session.refresh(student)
            self.assertEqual(sorted(s.name.lower() for s in student.skills), ["git", "python", "sql"])
            self.assertEqual((len(student.education), len(student.projects), len(student.experience)), (1, 1, 1))

    def test_gibberish_search_returns_nothing(self):
        r = self.client.post("/api/jobs/match", json={"query": "zzzzqq asdf"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["results"], [])
        r = self.client.post("/api/jobs/match", json={"query": "flutter"})
        self.assertTrue(r.get_json()["results"])

    def test_matching_api_and_agents(self):
        self.client.post("/profile/skill", data={"name": "Python", "category": "technical"})
        r = self.client.post("/api/jobs/match", json={"top_k": 5})
        self.assertEqual(r.status_code, 200)
        results = r.get_json()["results"]
        self.assertTrue(results)
        job_id = results[0]["job"]["job_id"]
        for path in ("/api/m3/skill-gap", "/api/m3/application", "/api/m3/interview"):
            self.assertEqual(self.client.post(path, json={"job_id": job_id}).status_code, 200, path)
        ev = self.client.post("/api/m3/mock-interview/evaluate", json={"job_id": job_id, "question": "Tell me about yourself", "answer": "I build Python projects."})
        self.assertEqual(ev.status_code, 200)
        self.assertIsNotNone(ev.get_json()["score"])

    def test_refine_falls_back_gracefully(self):
        r = self.client.post("/api/m3/application/refine", json={"job_id": "INT-001", "text": "Dear team", "instruction": "shorter"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["text"], "Dear team")

    def test_career_assistant_keeps_context(self):
        r1 = self.client.post("/api/m3/career/chat", json={"message": "Recommend suitable internships"})
        self.assertEqual(r1.status_code, 200)
        cid = r1.get_json()["conversation_id"]
        r2 = self.client.post("/api/m3/career/chat", json={"message": "Which skills should I learn?", "conversation_id": cid})
        self.assertEqual(r2.get_json()["conversation_id"], cid)
        history = self.client.get(f"/api/m3/career/conversations/{cid}").get_json()
        self.assertEqual(len(history["messages"]), 4)

    def test_tracker_lifecycle_filters_and_reminders(self):
        today = date.today()
        created = self.client.post("/api/applications", json={"job_id": "INT-001"})
        self.assertEqual(created.status_code, 201)
        app_id = created.get_json()["application"]["id"]
        self.assertIn("Responsibilities", created.get_json()["application"]["job_description"])
        # duplicate tracking of the same posting is idempotent
        self.assertTrue(self.client.post("/api/applications", json={"job_id": "INT-001"}).get_json()["existing"])

        patch = self.client.patch(f"/api/applications/{app_id}", json={
            "status": "interview_scheduled",
            "deadline": (today + timedelta(days=3)).isoformat(),
            "interview_date": (today + timedelta(days=5)).isoformat() + "T10:00",
            "interview_status": "scheduled",
            "follow_up_date": (today + timedelta(days=1)).isoformat(),
            "follow_up_note": "Email recruiter",
            "cover_letter": "Dear team", "tailored_resume": "SKILLS\nPython",
            "notes": "Great call",
        })
        self.assertEqual(patch.status_code, 200)
        record = patch.get_json()["application"]
        self.assertEqual(record["interview_status"], "scheduled")
        self.assertEqual(record["tailored_resume"], "SKILLS\nPython")

        self.client.post("/api/applications", json={"company": "Acme", "job_title": "Analyst", "status": "rejected"})
        stats = self.client.get("/api/applications/stats").get_json()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["interviews_scheduled"], 1)
        self.assertEqual(stats["rejected"], 1)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(len(stats["upcoming_deadlines"]), 1)
        self.assertEqual(len(stats["upcoming_interviews"]), 1)
        self.assertEqual(len(stats["follow_ups"]), 1)

        listing = lambda qs: self.client.get("/api/applications?" + qs).get_json()["applications"]
        self.assertEqual(len(listing("company=acme")), 1)
        self.assertEqual(len(listing("role=analyst")), 1)
        self.assertEqual(len(listing("status=rejected")), 1)
        self.assertEqual(len(listing("group=active")), 1)
        self.assertEqual(len(listing("group=completed")), 1)
        self.assertEqual(len(listing("deadline_to=" + (today + timedelta(days=4)).isoformat())), 1)
        self.assertEqual(listing("sort=company")[0]["company"], "Acme")

        self.assertEqual(self.client.patch(f"/api/applications/{app_id}", json={"status": "bogus"}).status_code, 400)
        self.assertEqual(self.client.delete(f"/api/applications/{app_id}").status_code, 200)

    def test_pending_applications_reminder(self):
        with app.app_context():
            student = Student.query.filter_by(email=self.email).first()
            from datetime import datetime
            stale = Application(student_id=student.id, company="Old Co", job_title="Intern", status="applied", updated_at=datetime.utcnow() - timedelta(days=10))
            db.session.add(stale)
            db.session.commit()
            db.session.execute(db.text("UPDATE applications SET updated_at = :t WHERE id = :i"), {"t": datetime.utcnow() - timedelta(days=10), "i": stale.id})
            db.session.commit()
        stats = self.client.get("/api/applications/stats").get_json()
        self.assertEqual(len(stats["pending_applications"]), 1)

    def test_cross_user_isolation(self):
        app_id = self.client.post("/api/applications", json={"company": "Private", "job_title": "Role"}).get_json()["application"]["id"]
        other = app.test_client()
        other.post("/register", data={"full_name": "Other", "email": f"o{os.urandom(3).hex()}@example.com", "password": "Password123", "confirm_password": "Password123"})
        self.assertEqual(other.get(f"/api/applications/{app_id}").status_code, 404)
        self.assertEqual(other.delete(f"/api/applications/{app_id}").status_code, 404)

    def test_pages_render(self):
        for path in ("/dashboard", "/profile", "/internships", "/career", "/applications", "/resume/upload"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.client.get("/settings").status_code, 200)
        self.assertEqual(app.test_client().get("/").status_code, 200)

    def test_404_pages(self):
        self.assertEqual(self.client.get("/does-not-exist").status_code, 404)
        r = self.client.get("/api/does-not-exist")
        self.assertEqual(r.status_code, 404)
        self.assertIsNotNone(r.get_json())

    def test_settings_export_and_password(self):
        r = self.client.get("/settings/export")
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.email, r.get_data(as_text=True))
        self.client.post("/settings/password", data={"current_password": "Password123", "new_password": "NewPass1234", "confirm_password": "NewPass1234"})
        c = app.test_client()
        r = c.post("/login", data={"email": self.email, "password": "NewPass1234"})
        self.assertEqual(r.status_code, 302)

    def test_settings_delete_account(self):
        r = self.client.post("/settings/delete", data={"password": "Password123"})
        self.assertEqual(r.status_code, 302)
        with app.app_context():
            self.assertIsNone(Student.query.filter_by(email=self.email).first())


if __name__ == "__main__":
    unittest.main()

"""Create (or refresh) a demo account with a parsed resume and sample applications.

Usage:  python seed_demo.py
Login:  demo@example.com / Demo@12345   (local demo only)
"""
import os
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

os.environ.setdefault("SEED_DEMO", "1")
from app import app, db  # noqa: E402
from models import Application, Student  # noqa: E402
from profile_m1 import merge_parsed_into_profile  # noqa: E402
from resume_service import parse_resume  # noqa: E402

EMAIL, PASSWORD = "demo@example.com", "Demo@12345"
SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "__DATA__", "file.pdf")


def main():
    with app.app_context():
        db.create_all()
        student = Student.query.filter_by(email=EMAIL).first()
        if not student:
            student = Student(full_name="Demo Student", email=EMAIL, password_hash=generate_password_hash(PASSWORD))
            db.session.add(student)
            db.session.commit()
        if not student.skills and os.path.exists(SAMPLE_PDF):
            parsed = parse_resume(SAMPLE_PDF)
            merge_parsed_into_profile(student, parsed)
            student.location = student.location or "Kochi, India"
            db.session.commit()
        if not Application.query.filter_by(student_id=student.id).count():
            today = date.today()
            rows = [
                ("TechNova Labs", "Python Backend Intern", "applied", today - timedelta(days=9), today + timedelta(days=3)),
                ("Northwind", "Data Analyst Intern", "saved", None, today + timedelta(days=8)),
                ("DataBridge Analytics", "Data Analyst Intern", "interview", today - timedelta(days=12), None),
                ("Orbit Systems", "Flutter Developer Intern", "offer", today - timedelta(days=30), None),
            ]
            for company, title, status, applied, deadline in rows:
                db.session.add(Application(student_id=student.id, company=company, job_title=title, status=status,
                                           applied_date=applied, deadline=deadline))
            db.session.commit()
        print(f"Demo ready: {EMAIL} / {PASSWORD}  (skills: {len(student.skills)}, applications: "
              f"{Application.query.filter_by(student_id=student.id).count()})")


if __name__ == "__main__":
    main()

from database import db
from models import Education, Experience, Project, Skill


def _value(item, key):
    value = item.get(key) if isinstance(item, dict) else None
    return value if value not in ("", None) else None


def _same(a, b):
    """Case/whitespace-insensitive equality for de-duplicating profile entries."""
    norm = lambda v: " ".join(str(v or "").lower().split())
    return bool(norm(a)) and norm(a) == norm(b)


def merge_parsed_into_profile(student, data, only_empty=True):
    # Scalar fields: preserve manual values by default.
    for field in ("full_name", "phone", "linkedin", "github", "portfolio"):
        incoming = _value(data, field)
        if incoming and (not only_empty or not getattr(student, field)):
            setattr(student, field, incoming)

    # Most specific categories first, so "Python" is filed under languages rather than generic technical.
    categories = [
        ("programming_languages", "languages"),
        ("frameworks", "frameworks"),
        ("databases", "databases"),
        ("tools", "tools"),
        ("soft_skills", "soft"),
        ("technical_skills", "technical"),
    ]
    seen = {str(x.name).strip().lower() for x in student.skills}
    for source, category in categories:
        for name in data.get(source, []) or []:
            clean = str(name or "").strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                db.session.add(Skill(student_id=student.id, category=category, name=clean))

    # To avoid duplicating records when a resume is re-parsed, only add entries
    # that do not already match a student's existing primary label.
    for item in data.get("education", []) or []:
        if not isinstance(item, dict):
            continue
        degree, institution = _value(item, "degree"), _value(item, "institution")
        if degree or institution:
            exists = any(
                (institution and _same(e.institution, institution)) or (not institution and _same(e.degree, degree))
                for e in list(student.education)
            )
            if not exists:
                db.session.add(Education(
                    student_id=student.id, degree=degree, institution=institution,
                    field_of_study=_value(item, "field_of_study"), start_date=_value(item, "start_date"),
                    end_date=_value(item, "end_date"), grade=_value(item, "grade"),
                    description=_value(item, "description")
                ))

    for item in data.get("experience", []) or []:
        if not isinstance(item, dict):
            continue
        company, title = _value(item, "company"), _value(item, "job_title") or _value(item, "title")
        if company or title:
            exists = any(
                _same(e.company, company) and (not title or not e.job_title or _same(e.job_title, title))
                for e in list(student.experience)
            )
            if not exists:
                db.session.add(Experience(
                    student_id=student.id, company=company, job_title=title,
                    location=_value(item, "location"), start_date=_value(item, "start_date"),
                    end_date=_value(item, "end_date"), description=_value(item, "description"),
                    technologies=item.get("technologies") or []
                ))

    for item in data.get("projects", []) or []:
        if not isinstance(item, dict):
            continue
        name = _value(item, "project_name") or _value(item, "name")
        if name and not any(_same(p.project_name, name) for p in list(student.projects)):
            db.session.add(Project(
                student_id=student.id, project_name=name, description=_value(item, "description"),
                technologies=item.get("technologies") or [], github_url=_value(item, "github_url"),
                live_url=_value(item, "live_url"), role=_value(item, "role")
            ))

    db.session.commit()


def completion_score(student):
    checks = [
        bool(student.full_name), bool(student.email), bool(student.phone), bool(student.location),
        bool(student.bio), bool(student.resumes), bool(student.skills), bool(student.education),
        bool(student.experience), bool(student.projects), bool(student.github), bool(student.linkedin)
    ]
    return round(sum(checks) / len(checks) * 100)

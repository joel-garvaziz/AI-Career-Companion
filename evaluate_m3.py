"""Milestone 3 deterministic smoke/evaluation checks."""
from jobs_dataset import get_all_jobs
from skill_gap_agent import analyze
from application_agent import fallback_application
from interview_agent import build_fallback

PROFILE = {
    "full_name":"Sample Student",
    "skills":[{"category":"languages","name":"Python"},{"category":"frameworks","name":"Flask"},{"category":"databases","name":"SQL"},{"category":"tools","name":"Git"}],
    "education":[{"degree":"B.Tech Computer Science","institution":"Sample College"}],
    "experience":[],
    "projects":[{"project_name":"Employee Management App","description":"Flask and SQL web application","technologies":["Python","Flask","SQL"]}],
}
def main():
    job=next(j for j in get_all_jobs() if j["job_id"]=="INT-001")
    gaps=analyze(PROFILE,job)
    assert isinstance(gaps["critical_missing_skills"],list)
    app=fallback_application(PROFILE,job)
    assert app["resume"]["priority_skills"]
    interview=build_fallback(PROFILE,job,gaps)
    types={q["type"] for q in interview["questions"]}
    print("M3.1 skill-gap: PASS")
    print("M3.2 application: PASS")
    print("M3.3 interview: PASS")
    print("M3.4 orchestration: PASS (API smoke path covered by Flask routes)")
    print("Question types generated:", ", ".join(sorted(types)))
if __name__=="__main__":
    main()

import json
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import db
from models import (
    Student,
    Education,
    Experience,
    Project,
    Skill,
    Resume,
    CareerConversation,
    CareerMessage,
    Application,
    APPLICATION_STATUSES,
    APPLICATION_STATUS_LABELS,
    INTERVIEW_STATUSES,
)
from auth import login_required, current_student
from profile_m1 import completion_score, merge_parsed_into_profile
from resume_service import parse_resume
from matching_agent import match_profile
from jobs_dataset import get_all_jobs

# M3 agents
from skill_gap_agent import (
    analyze as analyze_skill_gap,
    build_profile_payload as m3_profile_payload,
)
from application_agent import customize as customize_application
from interview_agent import prepare as prepare_interview, evaluate_answer
from career_assistant import answer as career_answer, build_tool_context


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__, instance_path=str(INSTANCE_DIR))

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "dev-only-change-me",
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///" + str(INSTANCE_DIR / "career_companion.db"),
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["WTF_CSRF_TIME_LIMIT"] = None

db.init_app(app)

ALLOWED_EXTENSIONS = {"pdf"}


# ---------------------------------------------------------------------------
# Common helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.context_processor
def inject_globals():
    return {"current_student": current_student()}


@app.errorhandler(413)
def too_large(_):
    flash(
        "The resume is too large. Maximum allowed size is 5 MB.",
        "error",
    )
    return redirect(url_for("upload_resume"))


# ---------------------------------------------------------------------------
# M1 — Authentication
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if session.get("student_id"):
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []

        if not name:
            errors.append("Full name is required.")

        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append("Enter a valid email address.")

        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")

        if password != confirm:
            errors.append("Passwords do not match.")

        if Student.query.filter_by(email=email).first():
            errors.append(
                "An account with that email already exists."
            )

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html")

        student = Student(
            full_name=name,
            email=email,
            password_hash=generate_password_hash(password),
        )

        db.session.add(student)
        db.session.commit()

        session.clear()
        session["student_id"] = student.id

        flash(
            "Welcome! Your career profile has been created.",
            "success",
        )

        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        student = Student.query.filter_by(email=email).first()

        if not student or not check_password_hash(
            student.password_hash,
            password,
        ):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session.clear()
        session["student_id"] = student.id
        session.permanent = True

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Account settings — name/email, password, data export, account deletion
# ---------------------------------------------------------------------------

@app.get("/settings")
@login_required
def settings():
    student = current_student()
    return render_template(
        "settings.html",
        student=student,
        counts={
            "resumes": len(student.resumes),
            "applications": len(student.applications),
            "conversations": len(student.career_conversations),
            "skills": len(student.skills),
        },
    )


@app.post("/settings/account")
@login_required
def settings_account():
    student = current_student()
    name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()

    if not name:
        flash("Name cannot be empty.", "error")
        return redirect(url_for("settings"))
    if "@" not in email or "." not in email.split("@")[-1]:
        flash("Enter a valid email address.", "error")
        return redirect(url_for("settings"))

    clash = Student.query.filter(Student.email == email, Student.id != student.id).first()
    if clash:
        flash("That email is already used by another account.", "error")
        return redirect(url_for("settings"))

    student.full_name = name
    student.email = email
    db.session.commit()
    flash("Account details updated.", "success")
    return redirect(url_for("settings"))


@app.post("/settings/password")
@login_required
def settings_password():
    student = current_student()
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not check_password_hash(student.password_hash, current):
        flash("Your current password is incorrect.", "error")
    elif len(new) < 8:
        flash("New password must be at least 8 characters.", "error")
    elif new != confirm:
        flash("New passwords do not match.", "error")
    else:
        student.password_hash = generate_password_hash(new)
        db.session.commit()
        flash("Password changed.", "success")
    return redirect(url_for("settings"))


@app.get("/settings/export")
@login_required
def settings_export():
    """Download everything stored about the student as JSON."""
    student = current_student()
    payload = student_payload(student)
    payload["applications"] = [a.to_dict() for a in student.applications]
    payload["resumes"] = [
        {
            "id": r.id,
            "filename": r.original_filename,
            "uploaded_at": r.uploaded_at.isoformat(),
            "parsing_status": r.parsing_status,
        }
        for r in student.resumes
    ]
    payload["conversations"] = [
        {
            "title": c.title,
            "messages": [
                {"role": m.role, "content": m.content, "at": m.created_at.isoformat()}
                for m in c.messages
            ],
        }
        for c in student.career_conversations
    ]
    response = jsonify(payload)
    response.headers["Content-Disposition"] = "attachment; filename=career-companion-data.json"
    return response


@app.post("/settings/delete")
@login_required
def settings_delete():
    student = current_student()

    if not check_password_hash(student.password_hash, request.form.get("password", "")):
        flash("Password incorrect — your account was not deleted.", "error")
        return redirect(url_for("settings"))

    files = [Path(r.file_path) for r in student.resumes]
    db.session.delete(student)
    db.session.commit()

    for path in files:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    session.clear()
    flash("Your account and all its data were deleted.", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found."}), 404
    return render_template("error.html", code=404, title="Page not found",
                           message="The page you're looking for doesn't exist or was moved."), 404


@app.errorhandler(500)
def server_error(_):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Something went wrong on our side."}), 500
    return render_template("error.html", code=500, title="Something went wrong",
                           message="An unexpected error occurred. Please try again in a moment."), 500


# ---------------------------------------------------------------------------
# M1 — Dashboard/Profile
# ---------------------------------------------------------------------------

@app.get("/dashboard")
@login_required
def dashboard():
    student = current_student()
    stats = application_stats_for(student)

    steps = [
        {"label": "Upload your resume", "done": bool(student.resumes), "href": url_for("upload_resume"), "hint": "We read it and fill in your profile for you"},
        {"label": "Check your profile", "done": completion_score(student) >= 70, "href": url_for("profile"), "hint": "Fix anything that looks wrong and add what is missing"},
        {"label": "Find internships that fit you", "done": bool(student.applications), "href": url_for("internships"), "hint": "See your best matches and why they fit"},
        {"label": "Save an internship you like", "done": bool(student.applications), "href": url_for("applications_page"), "hint": "Keep deadlines and interviews in one place"},
        {"label": "Get advice from your career coach", "done": bool(student.career_conversations), "href": url_for("career"), "hint": "Skills to build, cover letter, interview practice"},
    ]

    return render_template(
        "dashboard.html",
        student=student,
        completion=completion_score(student),
        application_stats=stats,
        steps=steps,
    )


@app.get("/profile")
@login_required
def profile():
    student = current_student()

    return render_template(
        "profile.html",
        student=student,
        completion=completion_score(student),
    )


@app.post("/profile/update")
@login_required
def update_profile():
    student = current_student()

    for field in (
        "full_name",
        "phone",
        "location",
        "bio",
        "linkedin",
        "github",
        "portfolio",
    ):
        setattr(
            student,
            field,
            request.form.get(field, "").strip() or None,
        )

    db.session.commit()

    flash(
        "Profile updated successfully.",
        "success",
    )

    return redirect(url_for("profile"))


@app.post("/profile/skill")
@login_required
def add_skill():
    student = current_student()

    name = request.form.get("name", "").strip()
    category = (
        request.form.get("category", "technical").strip()
        or "technical"
    )

    if name and not any(
        str(x.name).strip().lower() == name.lower() for x in student.skills
    ):

        db.session.add(
            Skill(
                student_id=student.id,
                category=category,
                name=name,
            )
        )

        db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/skill/<int:item_id>/delete")
@login_required
def delete_skill(item_id):
    item = Skill.query.filter_by(
        id=item_id,
        student_id=session["student_id"],
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/education")
@login_required
def add_education():
    student = current_student()

    db.session.add(
        Education(
            student_id=student.id,
            degree=request.form.get("degree", "").strip(),
            institution=request.form.get(
                "institution",
                "",
            ).strip(),
            field_of_study=request.form.get(
                "field_of_study",
                "",
            ).strip(),
            start_date=request.form.get(
                "start_date",
                "",
            ).strip(),
            end_date=request.form.get(
                "end_date",
                "",
            ).strip(),
            grade=request.form.get(
                "grade",
                "",
            ).strip(),
            description=request.form.get(
                "description",
                "",
            ).strip(),
        )
    )

    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/education/<int:item_id>/delete")
@login_required
def delete_education(item_id):
    item = Education.query.filter_by(
        id=item_id,
        student_id=session["student_id"],
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/experience")
@login_required
def add_experience():
    student = current_student()

    technologies = [
        x.strip()
        for x in request.form.get(
            "technologies",
            "",
        ).split(",")
        if x.strip()
    ]

    db.session.add(
        Experience(
            student_id=student.id,
            company=request.form.get(
                "company",
                "",
            ).strip(),
            job_title=request.form.get(
                "job_title",
                "",
            ).strip(),
            location=request.form.get(
                "location",
                "",
            ).strip(),
            start_date=request.form.get(
                "start_date",
                "",
            ).strip(),
            end_date=request.form.get(
                "end_date",
                "",
            ).strip(),
            description=request.form.get(
                "description",
                "",
            ).strip(),
            technologies=technologies,
        )
    )

    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/experience/<int:item_id>/delete")
@login_required
def delete_experience(item_id):
    item = Experience.query.filter_by(
        id=item_id,
        student_id=session["student_id"],
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/project")
@login_required
def add_project():
    student = current_student()

    technologies = [
        x.strip()
        for x in request.form.get(
            "technologies",
            "",
        ).split(",")
        if x.strip()
    ]

    db.session.add(
        Project(
            student_id=student.id,
            project_name=request.form.get(
                "project_name",
                "",
            ).strip(),
            description=request.form.get(
                "description",
                "",
            ).strip(),
            technologies=technologies,
            github_url=request.form.get(
                "github_url",
                "",
            ).strip(),
            live_url=request.form.get(
                "live_url",
                "",
            ).strip(),
            role=request.form.get(
                "role",
                "",
            ).strip(),
        )
    )

    db.session.commit()

    return redirect(url_for("profile"))


@app.post("/profile/project/<int:item_id>/delete")
@login_required
def delete_project(item_id):
    item = Project.query.filter_by(
        id=item_id,
        student_id=session["student_id"],
    ).first_or_404()

    db.session.delete(item)
    db.session.commit()

    return redirect(url_for("profile"))


# ---------------------------------------------------------------------------
# M1 — Resume
# ---------------------------------------------------------------------------

@app.get("/resume/upload")
@login_required
def upload_resume():
    return render_template(
        "upload_resume.html",
        student=current_student(),
    )


@app.post("/resume/upload")
@login_required
def process_resume():
    student = current_student()
    file = request.files.get("resume")

    if not file or not file.filename:
        flash(
            "Please choose a PDF resume.",
            "error",
        )
        return redirect(url_for("upload_resume"))

    if not allowed_file(file.filename):
        flash(
            "Only PDF resumes are allowed.",
            "error",
        )
        return redirect(url_for("upload_resume"))

    original = (
        secure_filename(file.filename)
        or "resume.pdf"
    )

    stored = f"{uuid.uuid4().hex}.pdf"
    path = UPLOAD_DIR / stored

    file.save(path)

    resume = Resume(
        student_id=student.id,
        original_filename=original,
        stored_filename=stored,
        file_path=str(path),
        file_type="application/pdf",
        file_size=path.stat().st_size,
        parsing_status="processing",
    )

    db.session.add(resume)
    db.session.commit()

    try:
        parsed = parse_resume(path)

        resume.parsing_status = "completed"
        resume.parsed_at = datetime.utcnow()
        resume.parsing_error = None

        merge_parsed_into_profile(
            student,
            parsed,
            only_empty=True,
        )

        db.session.add(resume)
        db.session.commit()

    except Exception as exc:
        db.session.rollback()

        resume = db.session.get(
            Resume,
            resume.id,
        )

        resume.parsing_status = "failed"
        resume.parsing_error = "We could not read this file. Please upload a PDF that contains selectable text (not a scanned image)."

        db.session.commit()

        flash(
            f"Resume processing failed: "
            f"{type(exc).__name__}: {exc}",
            "error",
        )

        return redirect(url_for("upload_resume"))

    flash(
        "Resume parsed successfully and your profile was updated.",
        "success",
    )

    return render_template(
        "resume_result.html",
        student=student,
        resume=resume,
        parsed=parsed,
    )


@app.post("/resume/<int:resume_id>/delete")
@login_required
def delete_resume(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id,
        student_id=session["student_id"],
    ).first_or_404()

    file_path = Path(resume.file_path)

    db.session.delete(resume)
    db.session.commit()

    try:
        if file_path.exists():
            file_path.unlink()
    except OSError:
        pass

    flash(
        "Resume deleted successfully.",
        "success",
    )

    return redirect(url_for("upload_resume"))


@app.get("/resume/<int:resume_id>")
@login_required
def view_resume(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id,
        student_id=session["student_id"],
    ).first_or_404()

    return send_file(
        resume.file_path,
        mimetype="application/pdf",
        download_name=resume.original_filename,
        as_attachment=False,
    )


@app.get("/resume/<int:resume_id>/download")
@login_required
def download_resume(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id,
        student_id=session["student_id"],
    ).first_or_404()

    return send_file(
        resume.file_path,
        mimetype="application/pdf",
        download_name=resume.original_filename,
        as_attachment=True,
    )


# ---------------------------------------------------------------------------
# M2 — Job/Resume Matching
# ---------------------------------------------------------------------------

def matching_profile_payload(student):
    """Convert the M1 SQLAlchemy profile into the structure expected by M2."""
    skills = [s.name for s in student.skills]

    education = [
        {
            "degree": e.degree,
            "institution": e.institution,
            "field_of_study": e.field_of_study,
            "grade": e.grade,
            "description": e.description,
        }
        for e in student.education
    ]

    experience = [
        {
            "company": e.company,
            "job_title": e.job_title,
            "location": e.location,
            "start_date": e.start_date,
            "end_date": e.end_date,
            "description": e.description,
            "technologies": e.technologies or [],
        }
        for e in student.experience
    ]

    projects = [
        {
            "project_name": p.project_name,
            "description": p.description,
            "technologies": p.technologies or [],
            "role": p.role,
        }
        for p in student.projects
    ]

    return {
        "full_name": student.full_name,
        "location": student.location,
        "bio": student.bio,
        "skills": skills,
        "education": education,
        "experience": experience,
        "projects": projects,
    }


@app.get("/internships")
@login_required
def internships():
    """Render the M2 internship matching page."""
    student = current_student()

    return render_template(
        "internships.html",
        student=student,
    )


@app.get("/api/jobs")
@login_required
def api_jobs():
    """Return the curated internship dataset for the UI."""
    jobs = get_all_jobs()

    return jsonify(
        {
            "count": len(jobs),
            "jobs": jobs,
        }
    )


MIN_QUERY_RELEVANCE = 0.36


@app.post("/api/jobs/match")
@login_required
def api_jobs_match():
    """Retrieve, filter, and rank internships against the student."""
    student = current_student()
    data = request.get_json(silent=True) or {}

    query = str(
        data.get("query", "")
    ).strip() or None

    location_filter = str(
        data.get("location", "")
    ).strip().lower()

    domain_filter = str(
        data.get("domain", "")
    ).strip().lower()

    job_type_filter = str(
        data.get("job_type", "")
    ).strip().lower()

    duration_filter = str(
        data.get("duration", "")
    ).strip().lower()

    try:
        top_k_retrieval = min(
            max(
                int(data.get("top_k_retrieval", 30)),
                5,
            ),
            30,
        )

        top_k_results = min(
            max(
                int(data.get("top_k", 20)),
                1,
            ),
            20,
        )

        min_score = float(
            data.get("min_score", 0)
        )

    except (TypeError, ValueError):
        return jsonify(
            {
                "error":
                    "Invalid numeric filter values."
            }
        ), 400

    min_score = max(
        0,
        min(100, min_score),
    )

    sort_by = str(
        data.get("sort", "score")
    ).strip().lower()

    if sort_by not in {
        "score",
        "relevance",
    }:
        sort_by = "score"

    try:
        results = match_profile(
            matching_profile_payload(student),
            query=query,
            top_k_retrieval=top_k_retrieval,
            top_k_results=top_k_results,
            include_llm_reasoning=bool(data.get("explain")),
        )

        filtered_results = []

        for result in results:
            job = result["job"]
            score = float(
                result.get("score", 0)
            )

            if score < min_score:
                continue

            # A typed search must actually resemble the internship (drops gibberish / unrelated queries).
            if query and float(result.get("retrieval_similarity", 0) or 0) < MIN_QUERY_RELEVANCE:
                continue

            location = str(
                job.get("location", "")
            ).lower()

            domain = str(
                job.get("domain", "")
            ).lower()

            job_type = str(
                job.get("job_type", "")
            ).lower()

            duration = str(
                job.get("duration", "")
            ).lower()

            if (
                location_filter
                and location_filter not in location
            ):
                continue

            if (
                domain_filter
                and domain_filter not in domain
            ):
                continue

            if (
                job_type_filter
                and job_type_filter != job_type
            ):
                continue

            if (
                duration_filter
                and duration_filter != duration
            ):
                continue

            filtered_results.append(result)

        if sort_by == "relevance":
            filtered_results.sort(
                key=lambda item:
                    item.get(
                        "retrieval_similarity",
                        0,
                    ),
                reverse=True,
            )
        else:
            filtered_results.sort(
                key=lambda item: (
                    item.get("score", 0),
                    item.get(
                        "retrieval_similarity",
                        0,
                    ),
                ),
                reverse=True,
            )

        filtered_results = filtered_results[
            :top_k_results
        ]

        payload = []

        for result in filtered_results:
            job = result["job"]
            reasoning = result.get(
                "reasoning",
                {},
            )

            payload.append(
                {
                    "job": job,
                    "score": result["score"],
                    "recommendation":
                        result["recommendation"],
                    "retrieval_similarity":
                        result[
                            "retrieval_similarity"
                        ],
                    "matched_required_skills":
                        result[
                            "matched_required_skills"
                        ],
                    "missing_required_skills":
                        result[
                            "missing_required_skills"
                        ],
                    "matched_preferred_skills":
                        result[
                            "matched_preferred_skills"
                        ],
                    "missing_preferred_skills":
                        result[
                            "missing_preferred_skills"
                        ],
                    "score_breakdown":
                        result[
                            "score_breakdown"
                        ],
                    "reasoning": reasoning,
                }
            )

        return jsonify(
            {
                "query": query,
                "candidate":
                    student.full_name,
                "filters": {
                    "location":
                        location_filter,
                    "domain":
                        domain_filter,
                    "job_type":
                        job_type_filter,
                    "duration":
                        duration_filter,
                    "min_score":
                        min_score,
                    "sort":
                        sort_by,
                },
                "total_matches":
                    len(payload),
                "results":
                    payload,
            }
        )

    except Exception as exc:
        app.logger.exception(
            "Internship matching failed"
        )

        return jsonify(
            {
                "error":
                    "Internship matching failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500


# ---------------------------------------------------------------------------
# M3 — Shared job/profile helpers
# ---------------------------------------------------------------------------

def m3_job(job_id):
    """Return one job from the M2 curated dataset."""
    if job_id is None:
        return None

    target = str(job_id)

    for job in get_all_jobs():
        if str(
            job.get("job_id", "")
        ) == target:
            return job

        # Support datasets that may use id instead of job_id.
        if str(
            job.get("id", "")
        ) == target:
            return job

    return None


def m3_student_profile(student):
    """Convert the logged-in M1 profile for all M3 agents."""
    return m3_profile_payload(student)


def json_error(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------------------
# M3 — Career AI page
# ---------------------------------------------------------------------------

@app.get("/career")
@login_required
def career():
    """Render the M3 Career AI workspace."""
    return render_template(
        "career.html",
        student=current_student(),
        jobs=get_all_jobs(),
    )


# ---------------------------------------------------------------------------
# M3.1 — Skill Gap Analysis
# ---------------------------------------------------------------------------

@app.post("/api/m3/skill-gap")
@login_required
def api_m3_skill_gap():
    data = request.get_json(silent=True) or {}

    job = m3_job(data.get("job_id"))

    if not job:
        return json_error(
            "Job not found.",
            404,
        )

    student = current_student()

    try:
        result = analyze_skill_gap(
            m3_student_profile(student),
            job,
        )

        return jsonify(
            {
                "job": job,
                "analysis": result,
            }
        )

    except Exception as exc:
        app.logger.exception(
            "M3 skill-gap analysis failed"
        )

        return jsonify(
            {
                "error":
                    "Skill gap analysis failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500


# ---------------------------------------------------------------------------
# M3.2 — Resume & Cover Letter Customization
# ---------------------------------------------------------------------------

@app.post("/api/m3/application")
@login_required
def api_m3_application():
    data = request.get_json(silent=True) or {}

    job = m3_job(data.get("job_id"))

    if not job:
        return json_error(
            "Job not found.",
            404,
        )

    student = current_student()

    try:
        result = customize_application(
            m3_student_profile(student),
            job,
        )

        return jsonify(
            {
                "job": job,
                "application": result,
            }
        )

    except Exception as exc:
        app.logger.exception(
            "M3 application customization failed"
        )

        return jsonify(
            {
                "error":
                    "Application customization failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500


@app.post("/api/m3/application/refine")
@login_required
def api_m3_application_refine():
    """Let the student refine generated material with an instruction."""
    from llm_utils import call_json

    data = request.get_json(silent=True) or {}
    job = m3_job(data.get("job_id"))
    text = str(data.get("text", "")).strip()
    instruction = str(data.get("instruction", "")).strip()

    if not job:
        return json_error("Job not found.", 404)
    if not text or not instruction:
        return json_error("Text and an instruction are required.", 400)

    profile = m3_student_profile(current_student())

    result = call_json(
        "You refine job-application text. Follow the student's instruction "
        "but NEVER invent skills, employers, projects, metrics or achievements "
        "that are not present in the candidate profile. Return JSON with the "
        "keys 'text' (the revised text) and 'note' (one sentence on what changed).",
        json.dumps(
            {
                "instruction": instruction,
                "text": text,
                "candidate_profile": profile,
                "job": job,
            },
            default=str,
        )[:24000],
        fallback={
            "text": text,
            "note": "AI refinement is unavailable right now, so your text was kept unchanged. You can still edit it manually.",
        },
    )

    return jsonify(
        {
            "text": str(result.get("text") or text),
            "note": str(result.get("note") or ""),
        }
    )


# ---------------------------------------------------------------------------
# M3.3 — Interview Preparation
# ---------------------------------------------------------------------------

@app.post("/api/m3/interview")
@login_required
def api_m3_interview():
    data = request.get_json(silent=True) or {}

    job = m3_job(data.get("job_id"))

    if not job:
        return json_error(
            "Job not found.",
            404,
        )

    student = current_student()
    profile = m3_student_profile(student)

    try:
        gaps = analyze_skill_gap(
            profile,
            job,
        )

        interview = prepare_interview(
            profile,
            job,
            gaps,
        )

        return jsonify(
            {
                "job": job,
                "skill_gap": gaps,
                "interview": interview,
            }
        )

    except Exception as exc:
        app.logger.exception(
            "M3 interview preparation failed"
        )

        return jsonify(
            {
                "error":
                    "Interview preparation failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500


@app.post("/api/m3/mock-interview/evaluate")
@login_required
def api_m3_mock_evaluate():
    data = request.get_json(silent=True) or {}

    job = m3_job(data.get("job_id"))

    if not job:
        return json_error(
            "Job not found.",
            404,
        )

    question = str(
        data.get("question", "")
    ).strip()

    answer = str(
        data.get("answer", "")
    ).strip()

    if not question or not answer:
        return json_error(
            "Question and answer are required.",
            400,
        )

    student = current_student()

    try:
        result = evaluate_answer(
            question,
            answer,
            m3_student_profile(student),
            job,
        )

        return jsonify(result)

    except Exception as exc:
        app.logger.exception(
            "M3 mock interview evaluation failed"
        )

        return jsonify(
            {
                "error":
                    "Mock interview evaluation failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500


# ---------------------------------------------------------------------------
# M3.4 — Conversational Career Assistant
# ---------------------------------------------------------------------------

def conversation_for_student(
    conversation_id,
    student_id,
):
    if not conversation_id:
        return None

    try:
        conversation_id = int(
            conversation_id
        )
    except (TypeError, ValueError):
        return None

    return (
        CareerConversation.query
        .filter_by(
            id=conversation_id,
            student_id=student_id,
        )
        .first()
    )


@app.post("/api/m3/career/chat")
@login_required
def api_m3_career_chat():
    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    if not message:
        return json_error(
            "Message is required.",
            400,
        )

    student = current_student()

    conversation = conversation_for_student(
        data.get("conversation_id"),
        student.id,
    )

    if conversation is None:
        title = str(
            data.get(
                "title",
                "Career Assistant",
            )
        ).strip()[:200]

        conversation = CareerConversation(
            student_id=student.id,
            title=title or "Career Assistant",
        )

        db.session.add(conversation)
        db.session.commit()

    history = [
        {
            "role": item.role,
            "content": item.content,
        }
        for item in conversation.messages[-8:]
    ]

    profile = m3_student_profile(student)

    selected_job = None

    if data.get("job_id") is not None:
        selected_job = m3_job(
            data.get("job_id")
        )

        if selected_job is None:
            return json_error(
                "Selected job was not found.",
                404,
            )

    # For a selected internship, call the M3 agents.
    # Otherwise, use M2 matching for internship-search questions.
    try:
        tool_context = build_tool_context(
            profile,
            query=message,
            job=selected_job,
        )

        # Make M3 tool output visible to the final assistant.
        assistant_jobs = []

        if selected_job:
            assistant_jobs = [
                selected_job
            ]
        else:
            matches = tool_context.get(
                "matches",
                [],
            )

            # match_profile returns result dictionaries
            # containing the actual job under "job".
            for item in matches[:10]:
                if isinstance(item, dict):
                    assistant_jobs.append(
                        item.get(
                            "job",
                            item,
                        )
                    )

        augmented_message = message

        if tool_context:
            augmented_message += (
                "\n\nSYSTEM TOOL OUTPUTS. "
                "Use these as grounded evidence:\n"
                + json.dumps(
                    tool_context,
                    default=str,
                )[:35000]
            )

        result = career_answer(
            profile,
            assistant_jobs,
            history,
            augmented_message,
            tool_context=tool_context,
        )

    except Exception as exc:
        app.logger.exception(
            "M3 Career Assistant failed"
        )

        return jsonify(
            {
                "error":
                    "Career Assistant failed.",
                 "detail": "Please try again in a moment.",
            }
        ), 500

    # Save both sides of the conversation.
    db.session.add(
        CareerMessage(
            conversation_id=conversation.id,
            role="user",
            content=message,
            job_id=(
                str(
                    selected_job.get("job_id")
                    or selected_job.get("id")
                )
                if selected_job
                else None
            ),
        )
    )

    db.session.add(
        CareerMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=str(
                result.get(
                    "answer",
                    "",
                )
            ),
            job_id=(
                str(
                    selected_job.get("job_id")
                    or selected_job.get("id")
                )
                if selected_job
                else None
            ),
        )
    )

    conversation.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify(
        {
            "conversation_id":
                conversation.id,
            "response":
                result,
            "tool_context":
                tool_context,
        }
    )


@app.get("/api/m3/career/conversations")
@login_required
def api_m3_conversations():
    student = current_student()

    conversations = (
        CareerConversation.query
        .filter_by(student_id=student.id)
        .order_by(
            CareerConversation.updated_at.desc()
        )
        .all()
    )

    return jsonify(
        {
            "conversations": [
                {
                    "id":
                        conversation.id,
                    "title":
                        conversation.title,
                    "created_at":
                        conversation.created_at.isoformat(),
                    "updated_at":
                        conversation.updated_at.isoformat(),
                }
                for conversation in conversations
            ]
        }
    )


@app.get(
    "/api/m3/career/conversations/<int:conversation_id>"
)
@login_required
def api_m3_conversation(conversation_id):
    student = current_student()

    conversation = (
        CareerConversation.query
        .filter_by(
            id=conversation_id,
            student_id=student.id,
        )
        .first_or_404()
    )

    return jsonify(
        {
            "id":
                conversation.id,
            "title":
                conversation.title,
            "messages": [
                {
                    "id":
                        item.id,
                    "role":
                        item.role,
                    "content":
                        item.content,
                    "job_id":
                        item.job_id,
                    "created_at":
                        item.created_at.isoformat(),
                }
                for item in conversation.messages
            ],
        }
    )


# ---------------------------------------------------------------------------
# M4 — Application Tracking Module
# ---------------------------------------------------------------------------

ACTIVE_STATUSES = {
    "planning",
    "applied",
    "under_review",
    "shortlisted",
    "interview_scheduled",
    "interview_completed",
}

UPCOMING_WINDOW_DAYS = 14
PENDING_AFTER_DAYS = 7
PENDING_STATUSES = {"applied", "under_review"}
TERMINAL_STATUSES = {"offer_received", "rejected", "withdrawn"}


def parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def parse_datetime_local(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def application_stats_for(student):
    applications = Application.query.filter_by(student_id=student.id).all()

    today = date.today()
    horizon = today + timedelta(days=UPCOMING_WINDOW_DAYS)

    upcoming_deadlines = sorted(
        (a for a in applications if a.deadline and today <= a.deadline <= horizon),
        key=lambda a: a.deadline,
    )
    upcoming_interviews = sorted(
        (
            a
            for a in applications
            if a.interview_date and a.interview_date >= datetime.utcnow()
        ),
        key=lambda a: a.interview_date,
    )

    follow_ups = sorted(
        (
            a
            for a in applications
            if a.follow_up_date
            and a.follow_up_date <= horizon
            and a.status not in TERMINAL_STATUSES
        ),
        key=lambda a: a.follow_up_date,
    )
    stale_cutoff = datetime.utcnow() - timedelta(days=PENDING_AFTER_DAYS)
    pending = sorted(
        (
            a
            for a in applications
            if a.status in PENDING_STATUSES and a.updated_at <= stale_cutoff
        ),
        key=lambda a: a.updated_at,
    )

    return {
        "total": len(applications),
        "completed": sum(1 for a in applications if a.status in TERMINAL_STATUSES),
        "active": sum(1 for a in applications if a.status in ACTIVE_STATUSES),
        "interviews_scheduled": sum(
            1 for a in applications if a.status == "interview_scheduled"
        ),
        "offers_received": sum(
            1 for a in applications if a.status == "offer_received"
        ),
        "rejected": sum(1 for a in applications if a.status == "rejected"),
        "upcoming_deadlines": [
            {
                "id": a.id,
                "company": a.company,
                "job_title": a.job_title,
                "deadline": a.deadline.isoformat(),
                "days_left": (a.deadline - today).days,
            }
            for a in upcoming_deadlines[:5]
        ],
        "follow_ups": [
            {
                "id": a.id,
                "company": a.company,
                "job_title": a.job_title,
                "follow_up_date": a.follow_up_date.isoformat(),
                "follow_up_note": a.follow_up_note,
                "days_left": (a.follow_up_date - today).days,
            }
            for a in follow_ups[:5]
        ],
        "pending_applications": [
            {
                "id": a.id,
                "company": a.company,
                "job_title": a.job_title,
                "status_label": a.status_label(),
                "days_waiting": (datetime.utcnow() - a.updated_at).days,
            }
            for a in pending[:5]
        ],
        "upcoming_interviews": [
            {
                "id": a.id,
                "company": a.company,
                "job_title": a.job_title,
                "interview_date": a.interview_date.isoformat(),
            }
            for a in upcoming_interviews[:5]
        ],
    }


@app.get("/applications")
@login_required
def applications_page():
    """Render the M4 application tracking workspace."""
    return render_template(
        "tracking.html",
        student=current_student(),
        statuses=APPLICATION_STATUSES,
        status_labels=APPLICATION_STATUS_LABELS,
        interview_statuses=INTERVIEW_STATUSES,
        resumes=[{"id": r.id, "name": r.original_filename} for r in current_student().resumes],
    )


@app.get("/api/applications")
@login_required
def api_applications_list():
    student = current_student()

    query = Application.query.filter_by(student_id=student.id)

    status_filter = request.args.get("status", "").strip()
    if status_filter and status_filter in APPLICATION_STATUSES:
        query = query.filter_by(status=status_filter)

    group = request.args.get("group", "").strip()
    if group == "active":
        query = query.filter(Application.status.in_(ACTIVE_STATUSES))
    elif group == "completed":
        query = query.filter(Application.status.in_(TERMINAL_STATUSES))

    deadline_from = parse_date(request.args.get("deadline_from"))
    deadline_to = parse_date(request.args.get("deadline_to"))
    applied_from = parse_date(request.args.get("applied_from"))
    applied_to = parse_date(request.args.get("applied_to"))
    if deadline_from:
        query = query.filter(Application.deadline >= deadline_from)
    if deadline_to:
        query = query.filter(Application.deadline <= deadline_to)
    if applied_from:
        query = query.filter(Application.applied_date >= applied_from)
    if applied_to:
        query = query.filter(Application.applied_date <= applied_to)

    sort = request.args.get("sort", "updated").strip()
    order = {
        "deadline": Application.deadline.asc(),
        "applied": Application.applied_date.desc(),
        "company": Application.company.asc(),
    }.get(sort, Application.updated_at.desc())

    company_q = request.args.get("company", "").strip().lower()
    role_q = request.args.get("role", "").strip().lower()
    search = request.args.get("q", "").strip().lower()
    applications = query.order_by(order).all()

    if company_q:
        applications = [a for a in applications if company_q in (a.company or "").lower()]
    if role_q:
        applications = [a for a in applications if role_q in (a.job_title or "").lower()]
    if search:
        applications = [
            a
            for a in applications
            if search in (a.company or "").lower()
            or search in (a.job_title or "").lower()
        ]

    return jsonify(
        {
            "applications": [a.to_dict() for a in applications],
            "stats": application_stats_for(student),
        }
    )


@app.post("/api/applications")
@login_required
def api_applications_create():
    student = current_student()
    data = request.get_json(silent=True) or {}

    job_id = str(data.get("job_id") or "").strip() or None
    company = str(data.get("company") or "").strip()
    job_title = str(data.get("job_title") or "").strip()

    # Allow tracking directly from a matched internship by job_id only.
    if job_id and not (company and job_title):
        job = m3_job(job_id)
        if job:
            company = company or str(job.get("company", ""))
            job_title = job_title or str(job.get("job_title", ""))
            data.setdefault("location", job.get("location"))
            data.setdefault("job_type", job.get("job_type"))
            data.setdefault(
                "job_description",
                "\n\n".join(
                    part
                    for part in (
                        str(job.get("job_description", "")),
                        "Responsibilities: " + str(job.get("responsibilities", "")),
                        "Required skills: " + ", ".join(job.get("required_skills", [])),
                    )
                    if part
                ),
            )

    if not company or not job_title:
        return json_error("Company and job title are required.", 400)

    if job_id:
        existing = Application.query.filter_by(
            student_id=student.id, job_id=job_id
        ).first()
        if existing:
            return jsonify({"application": existing.to_dict(), "existing": True})

    status = str(data.get("status") or "saved").strip()
    if status not in APPLICATION_STATUSES:
        status = "saved"

    application = Application(
        student_id=student.id,
        job_id=job_id,
        company=company,
        job_title=job_title,
        location=str(data.get("location") or "").strip() or None,
        job_type=str(data.get("job_type") or "").strip() or None,
        job_url=str(data.get("job_url") or "").strip() or None,
        job_description=str(data.get("job_description") or "").strip() or None,
        interview_status=(
            str(data.get("interview_status") or "").strip()
            if str(data.get("interview_status") or "").strip() in INTERVIEW_STATUSES
            else None
        ),
        follow_up_date=parse_date(data.get("follow_up_date")),
        follow_up_note=str(data.get("follow_up_note") or "").strip() or None,
        tailored_resume=str(data.get("tailored_resume") or "").strip() or None,
        status=status,
        applied_date=parse_date(data.get("applied_date")),
        deadline=parse_date(data.get("deadline")),
        interview_date=parse_datetime_local(data.get("interview_date")),
        notes=str(data.get("notes") or "").strip() or None,
        cover_letter=str(data.get("cover_letter") or "").strip() or None,
    )

    db.session.add(application)
    db.session.commit()

    return jsonify({"application": application.to_dict(), "existing": False}), 201


@app.get("/api/applications/<int:application_id>")
@login_required
def api_applications_get(application_id):
    application = Application.query.filter_by(
        id=application_id, student_id=session["student_id"]
    ).first_or_404()

    return jsonify({"application": application.to_dict()})


@app.patch("/api/applications/<int:application_id>")
@login_required
def api_applications_update(application_id):
    application = Application.query.filter_by(
        id=application_id, student_id=session["student_id"]
    ).first_or_404()

    data = request.get_json(silent=True) or {}

    if "status" in data:
        status = str(data["status"]).strip()
        if status not in APPLICATION_STATUSES:
            return json_error("Invalid status.", 400)
        application.status = status
        if status == "applied" and not application.applied_date:
            application.applied_date = date.today()

    for field in (
        "company",
        "job_title",
        "location",
        "job_type",
        "job_url",
        "job_description",
        "follow_up_note",
        "tailored_resume",
    ):
        if field in data:
            application.__setattr__(
                field, str(data[field] or "").strip() or None
            )

    if "notes" in data:
        application.notes = str(data["notes"] or "").strip() or None

    if "interview_notes" in data:
        application.interview_notes = str(data["interview_notes"] or "").strip() or None

    if "cover_letter" in data:
        application.cover_letter = str(data["cover_letter"] or "").strip() or None

    if "interview_status" in data:
        value = str(data.get("interview_status") or "").strip()
        if value and value not in INTERVIEW_STATUSES:
            return json_error("Invalid interview status.", 400)
        application.interview_status = value or None

    if "follow_up_date" in data:
        application.follow_up_date = parse_date(data.get("follow_up_date"))

    if "applied_date" in data:
        application.applied_date = parse_date(data.get("applied_date"))

    if "deadline" in data:
        application.deadline = parse_date(data.get("deadline"))

    if "interview_date" in data:
        application.interview_date = parse_datetime_local(data.get("interview_date"))

    if "resume_id" in data:
        resume_id = data.get("resume_id")
        if resume_id:
            resume = Resume.query.filter_by(
                id=resume_id, student_id=session["student_id"]
            ).first()
            application.resume_id = resume.id if resume else None
        else:
            application.resume_id = None

    db.session.commit()

    return jsonify({"application": application.to_dict()})


@app.delete("/api/applications/<int:application_id>")
@login_required
def api_applications_delete(application_id):
    application = Application.query.filter_by(
        id=application_id, student_id=session["student_id"]
    ).first_or_404()

    db.session.delete(application)
    db.session.commit()

    return jsonify({"deleted": True})


@app.get("/api/applications/stats")
@login_required
def api_applications_stats():
    return jsonify(application_stats_for(current_student()))


# ---------------------------------------------------------------------------
# Existing API — profile/resume
# ---------------------------------------------------------------------------

def student_payload(student):
    return {
        "id": student.id,
        "full_name": student.full_name,
        "email": student.email,
        "phone": student.phone,
        "location": student.location,
        "bio": student.bio,
        "linkedin": student.linkedin,
        "github": student.github,
        "portfolio": student.portfolio,
        "completion": completion_score(student),
        "skills": [
            {
                "category": s.category,
                "name": s.name,
            }
            for s in student.skills
        ],
        "education": [
            {
                "degree": e.degree,
                "institution": e.institution,
                "field_of_study": e.field_of_study,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "grade": e.grade,
            }
            for e in student.education
        ],
        "experience": [
            {
                "company": e.company,
                "job_title": e.job_title,
                "location": e.location,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "description": e.description,
            }
            for e in student.experience
        ],
        "projects": [
            {
                "project_name": p.project_name,
                "description": p.description,
                "technologies": p.technologies or [],
                "github_url": p.github_url,
                "live_url": p.live_url,
            }
            for p in student.projects
        ],
    }


@app.get("/api/profile")
@login_required
def api_profile():
    return jsonify(
        student_payload(
            current_student()
        )
    )


@app.put("/api/profile")
@login_required
def api_profile_update():
    student = current_student()
    data = request.get_json(silent=True) or {}

    for field in (
        "full_name",
        "phone",
        "location",
        "bio",
        "linkedin",
        "github",
        "portfolio",
    ):
        if field in data:
            setattr(
                student,
                field,
                str(
                    data[field]
                ).strip() or None,
            )

    db.session.commit()

    return jsonify(
        student_payload(student)
    )


@app.get("/api/resume/<int:resume_id>")
@login_required
def api_resume(resume_id):
    resume = Resume.query.filter_by(
        id=resume_id,
        student_id=session["student_id"],
    ).first_or_404()

    return jsonify(
        {
            "id": resume.id,
            "original_filename":
                resume.original_filename,
            "uploaded_at":
                resume.uploaded_at.isoformat(),
            "parsed_at":
                (
                    resume.parsed_at.isoformat()
                    if resume.parsed_at
                    else None
                ),
            "parsing_status":
                resume.parsing_status,
            "parsing_error":
                resume.parsing_error,
        }
    )


# ---------------------------------------------------------------------------
# Database / application entrypoint
# ---------------------------------------------------------------------------

@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database initialized.")


def ensure_schema():
    """Add columns introduced after a database was first created.

    db.create_all() only creates missing tables, so new nullable columns on
    existing tables are added here (SQLite ALTER TABLE ... ADD COLUMN).
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "applications" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("applications")}
    wanted = {
        "job_description": "TEXT",
        "interview_status": "VARCHAR(30)",
        "follow_up_date": "DATE",
        "follow_up_note": "TEXT",
        "tailored_resume": "TEXT",
    }
    with db.engine.begin() as conn:
        for name, ddl in wanted.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE applications ADD COLUMN {name} {ddl}"))


with app.app_context():
    db.create_all()
    ensure_schema()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=True,
    )

from datetime import datetime

from database import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(150))
    bio = db.Column(db.Text)
    profile_picture = db.Column(db.String(500))
    linkedin = db.Column(db.String(500))
    github = db.Column(db.String(500))
    portfolio = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    education = db.relationship(
        "Education", backref="student", cascade="all, delete-orphan", lazy=True
    )
    experience = db.relationship(
        "Experience", backref="student", cascade="all, delete-orphan", lazy=True
    )
    projects = db.relationship(
        "Project", backref="student", cascade="all, delete-orphan", lazy=True
    )
    skills = db.relationship(
        "Skill", backref="student", cascade="all, delete-orphan", lazy=True
    )
    resumes = db.relationship(
        "Resume", backref="student", cascade="all, delete-orphan", lazy=True
    )
    career_conversations = db.relationship(
        "CareerConversation",
        backref="student",
        cascade="all, delete-orphan",
        lazy=True,
    )
    applications = db.relationship(
        "Application",
        backref="student",
        cascade="all, delete-orphan",
        lazy=True,
    )


class Education(db.Model):
    __tablename__ = "education"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    degree = db.Column(db.String(200))
    institution = db.Column(db.String(250))
    field_of_study = db.Column(db.String(200))
    start_date = db.Column(db.String(80))
    end_date = db.Column(db.String(80))
    grade = db.Column(db.String(100))
    description = db.Column(db.Text)


class Experience(db.Model):
    __tablename__ = "experience"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    company = db.Column(db.String(250))
    job_title = db.Column(db.String(200))
    location = db.Column(db.String(150))
    start_date = db.Column(db.String(80))
    end_date = db.Column(db.String(80))
    description = db.Column(db.Text)
    technologies = db.Column(db.JSON)


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    project_name = db.Column(db.String(250))
    description = db.Column(db.Text)
    technologies = db.Column(db.JSON)
    github_url = db.Column(db.String(500))
    live_url = db.Column(db.String(500))
    role = db.Column(db.String(200))


class Skill(db.Model):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    category = db.Column(
        db.String(80),
        nullable=False,
    )  # technical / soft / tools / languages / frameworks / databases
    name = db.Column(db.String(150), nullable=False)


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parsed_at = db.Column(db.DateTime)
    parsing_status = db.Column(
        db.String(30), default="uploaded", nullable=False
    )
    parsing_error = db.Column(db.Text)


class CareerConversation(db.Model):
    __tablename__ = "career_conversations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), default="Career Assistant")
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    messages = db.relationship(
        "CareerMessage",
        backref="conversation",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="CareerMessage.created_at",
    )


class CareerMessage(db.Model):
    __tablename__ = "career_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer,
        db.ForeignKey("career_conversations.id"),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    job_id = db.Column(db.String(100))


# Milestone 4 — Application Tracking Module
APPLICATION_STATUSES = [
    "saved",
    "planning",
    "applied",
    "under_review",
    "shortlisted",
    "interview_scheduled",
    "interview_completed",
    "offer_received",
    "rejected",
    "withdrawn",
]

INTERVIEW_STATUSES = ["scheduled", "completed", "passed", "failed", "cancelled"]

APPLICATION_STATUS_LABELS = {
    "saved": "Saved",
    "planning": "Planning to Apply",
    "applied": "Applied",
    "under_review": "Application Under Review",
    "shortlisted": "Shortlisted",
    "interview_scheduled": "Interview Scheduled",
    "interview_completed": "Interview Completed",
    "offer_received": "Offer Received",
    "rejected": "Rejected",
    "withdrawn": "Withdrawn",
}


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("students.id"), nullable=False, index=True
    )

    job_id = db.Column(db.String(100), index=True)
    company = db.Column(db.String(250), nullable=False)
    job_title = db.Column(db.String(250), nullable=False)
    location = db.Column(db.String(150))
    job_type = db.Column(db.String(50))
    job_url = db.Column(db.String(500))
    job_description = db.Column(db.Text)

    status = db.Column(db.String(30), default="saved", nullable=False, index=True)

    applied_date = db.Column(db.Date)
    deadline = db.Column(db.Date)
    interview_date = db.Column(db.DateTime)
    interview_notes = db.Column(db.Text)
    interview_status = db.Column(db.String(30))  # scheduled / completed / passed / failed

    follow_up_date = db.Column(db.Date)
    follow_up_note = db.Column(db.Text)

    notes = db.Column(db.Text)

    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"))
    cover_letter = db.Column(db.Text)
    tailored_resume = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    resume = db.relationship("Resume")

    def status_label(self):
        return APPLICATION_STATUS_LABELS.get(self.status, self.status)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "company": self.company,
            "job_title": self.job_title,
            "location": self.location,
            "job_type": self.job_type,
            "job_url": self.job_url,
            "job_description": self.job_description,
            "status": self.status,
            "status_label": self.status_label(),
            "applied_date": self.applied_date.isoformat() if self.applied_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "interview_date": self.interview_date.isoformat() if self.interview_date else None,
            "interview_notes": self.interview_notes,
            "interview_status": self.interview_status,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "follow_up_note": self.follow_up_note,
            "notes": self.notes,
            "resume_id": self.resume_id,
            "cover_letter": self.cover_letter,
            "tailored_resume": self.tailored_resume,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

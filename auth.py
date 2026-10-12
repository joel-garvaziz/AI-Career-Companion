from functools import wraps
from flask import session, redirect, url_for, flash
from models import Student
from database import db


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        student_id = session.get("student_id")
        if not student_id or not db.session.get(Student, student_id):
            session.clear()
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_student():
    student_id = session.get("student_id")
    return db.session.get(Student, student_id) if student_id else None

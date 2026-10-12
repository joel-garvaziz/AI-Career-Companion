
"""Milestone 3.2 — Resume & Cover Letter Customization Agent."""
from __future__ import annotations
from typing import Any, Dict
from llm_utils import call_json

def fallback_application(profile: Dict[str,Any], job: Dict[str,Any]) -> Dict[str,Any]:
    skills=[x.get("name") for x in profile.get("skills",[]) if isinstance(x,dict)]
    relevant=[s for s in job.get("required_skills",[]) if s in skills]
    projects=profile.get("projects",[]) or []
    project_lines=[{"project_name":p.get("project_name"),"description":p.get("description"),"technologies":p.get("technologies",[])} for p in projects[:5]]
    name=profile.get("full_name") or "Candidate"
    cover=f"""Dear Hiring Team,

I am writing to apply for the {job.get('job_title','Internship')} opportunity at {job.get('company','the company')}. My background in {', '.join(relevant[:5]) or 'computer science and software development'} and my academic projects have given me practical experience relevant to this role.

I am particularly interested in the opportunity to contribute to the responsibilities described in the internship posting while continuing to develop my technical skills.

Thank you for considering my application.

Sincerely,
{name}"""
    return {
        "resume": {
            "headline":f"{job.get('job_title','Intern')} | {', '.join(relevant[:6])}",
            "priority_skills":relevant,
            "priority_projects":project_lines,
            "section_order":["Summary","Skills","Projects","Experience","Education"],
            "bullet_improvements":[
                {"original":p.get("description",""),"suggested":p.get("description","")} for p in projects[:5]
            ],
            "keywords_used":relevant,
        },
        "cover_letter":cover,
        "warnings":["Only information present in the stored profile was used. Review all generated content before submitting."]
    }

def customize(profile: Dict[str,Any], job: Dict[str,Any]) -> Dict[str,Any]:
    fallback=fallback_application(profile,job)
    prompt=f"""Tailor application materials for this internship. Use ONLY the candidate evidence supplied. Do not invent skills, metrics, responsibilities, companies, dates, awards, certifications, or achievements. Job keywords may be used only when supported by candidate evidence; otherwise list them as keywords to consider learning, not as candidate skills.

CANDIDATE PROFILE:
{profile}

JOB POSTING:
{job}

Return JSON exactly:
{{
 "resume": {{
   "headline": "...",
   "professional_summary": "...",
   "priority_skills": [],
   "priority_projects": [{{"project_name":"...","reason":"...","tailored_bullets":[]}}],
   "priority_experience": [{{"company":"...","job_title":"...","reason":"...","tailored_bullets":[]}}],
   "section_order": [],
   "keywords_used": [],
   "keywords_not_supported": [],
   "bullet_improvements": [{{"original":"...","suggested":"..."}}]
 }},
 "cover_letter": "...",
 "warnings": []
}}
"""
    return call_json(
        "You are a conservative resume and cover-letter customization agent. Preserve factual integrity and explicitly flag unsupported job keywords.",
        prompt, fallback
    )

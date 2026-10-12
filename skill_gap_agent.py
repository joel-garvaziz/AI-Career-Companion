
"""Milestone 3.1 — Skill Gap Analysis Agent."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Set
from llm_utils import call_json

def norm(v: Any) -> str:
    return re.sub(r"[^a-z0-9+#.\- ]+", " ", str(v or "").lower()).strip()

def terms(values: Any) -> Set[str]:
    if values is None: return set()
    if isinstance(values, str): values=re.split(r"[,;\n|]", values)
    return {norm(v) for v in values if norm(v)}

def profile_skill_set(profile: Dict[str, Any]) -> Set[str]:
    out=set()
    for key in ("skills","technical_skills","soft_skills","tools","programming_languages","frameworks","databases"):
        v=profile.get(key, [])
        if isinstance(v, list): out |= terms(v)
        else: out |= terms(v)
    for exp in profile.get("experience",[]) or []:
        out |= terms(exp.get("technologies",[]) if isinstance(exp,dict) else [])
    for p in profile.get("projects",[]) or []:
        out |= terms(p.get("technologies",[]) if isinstance(p,dict) else [])
    return out

def match_state(candidate: Set[str], required: str) -> str:
    r=norm(required)
    if r in candidate: return "demonstrated"
    if any(r in c or c in r for c in candidate): return "demonstrated"
    # A partially demonstrated skill is supported by related evidence.
    aliases={
        "rest apis":{"api","apis","flask","fastapi","backend"},
        "machine learning":{"ml","machine learning","tensorflow","pytorch","scikit-learn"},
        "data analysis":{"pandas","numpy","sql","data analysis"},
        "sql":{"mysql","postgresql","pl/sql","sql"},
        "git":{"github","git"},
        "docker":{"docker","container","containers"},
        "communication":{"communication","collaboration","teamwork"},
    }
    for k, related in aliases.items():
        if r==k and candidate & related: return "partial"
    return "missing"

def build_profile_payload(student) -> Dict[str,Any]:
    return {
        "full_name":student.full_name,"location":student.location,"bio":student.bio,
        "skills":[{"category":s.category,"name":s.name} for s in student.skills],
        "education":[{"degree":e.degree,"institution":e.institution,"field_of_study":e.field_of_study,"grade":e.grade,"description":e.description} for e in student.education],
        "experience":[{"company":e.company,"job_title":e.job_title,"location":e.location,"start_date":e.start_date,"end_date":e.end_date,"description":e.description,"technologies":e.technologies or []} for e in student.experience],
        "projects":[{"project_name":p.project_name,"description":p.description,"technologies":p.technologies or [],"role":p.role} for p in student.projects],
    }


ADJACENT = {
    "fastapi": ["flask", "django", "rest api", "python"],
    "django": ["flask", "python"], "flask": ["django", "fastapi", "python"],
    "docker": ["linux", "aws", "ci/cd", "git"], "kubernetes": ["docker", "aws"],
    "aws": ["docker", "linux", "ci/cd"], "postgresql": ["mysql", "sql"], "mysql": ["sql", "postgresql"],
    "mongodb": ["sql", "mysql", "firebase"], "react": ["javascript", "html", "css"],
    "typescript": ["javascript"], "pytorch": ["tensorflow", "python", "machine learning"],
    "tensorflow": ["pytorch", "python", "machine learning"], "machine learning": ["python", "scikit-learn", "tensorflow", "pytorch"],
    "pandas": ["python", "numpy", "sql"], "data analysis": ["python", "sql", "pandas"], "rest apis": ["flask", "api"],
    "communication": ["teamwork", "collaboration", "mentor"], "git": ["github"],
}
LEARN_DAYS = {"fastapi": 5, "django": 10, "docker": 5, "kubernetes": 14, "aws": 10, "typescript": 7, "react": 14, "pytorch": 14,
              "tensorflow": 14, "postgresql": 4, "mongodb": 5, "communication": 14, "pandas": 7, "machine learning": 21}


def evidence_for(skill: str, profile: Dict[str, Any]) -> List[str]:
    """Where in the candidate's own profile a skill (or an adjacent one) is actually used."""
    key = norm(skill)
    hits: List[str] = []
    for p in profile.get("projects", []) or []:
        if not isinstance(p, dict):
            continue
        blob = norm(" ".join([str(p.get("project_name", "")), str(p.get("description", "")), " ".join(map(str, p.get("technologies") or []))]))
        if key and key in blob:
            hits.append(f"project '{p.get('project_name')}'")
    for e in profile.get("experience", []) or []:
        if not isinstance(e, dict):
            continue
        blob = norm(" ".join([str(e.get("description", "")), " ".join(map(str, e.get("technologies") or []))]))
        if key and key in blob:
            hits.append(f"your {e.get('job_title') or 'role'} at {e.get('company')}")
    return hits[:2]


def adjacent_evidence(skill: str, profile: Dict[str, Any]):
    """(adjacent skill the candidate already has, where they used it)."""
    have = profile_skill_set(profile)
    for adj in ADJACENT.get(norm(skill), []):
        if adj in have or any(adj in h for h in have):
            return adj, evidence_for(adj, profile)
    return None, []


def role_context(skill: str, job: Dict[str, Any]) -> str:
    """The job's own words about where this skill is used."""
    key = norm(skill)
    for r in job.get("responsibilities", []) or []:
        if key and key in norm(r):
            return str(r).rstrip(".")
    desc = str(job.get("job_description") or "")
    for sent in re.split(r"(?<=[.!?])\s+", desc):
        if key and key in norm(sent):
            return sent.rstrip(".")
    return ""


def tailored_gap(skill: str, kind: str, profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, str]:
    title = job.get("job_title", "this role")
    company = job.get("company", "the company")
    ctx = role_context(skill, job)
    why = f"{company} lists {skill} as {'required' if kind == 'required' else 'a plus'} for the {title}"
    why += f" - the posting mentions: \"{ctx}\"." if ctx else "."
    adj, where = adjacent_evidence(skill, profile)
    if adj:
        loc = f" ({where[0]})" if where else ""
        why += f" You already work with {adj}{loc}, so this is a short step."
    return {"skill": skill, "why_important": why}


def tailored_action(skill: str, profile: Dict[str, Any], job: Dict[str, Any]) -> str:
    days = LEARN_DAYS.get(norm(skill), 7)
    adj, where = adjacent_evidence(skill, profile)
    projects = [p.get("project_name") for p in profile.get("projects", []) or [] if isinstance(p, dict) and p.get("project_name")]
    if norm(skill) == "communication":
        return (f"Over ~{days} days: write a clear README and a 5-minute walkthrough for "
                f"{projects[0] if projects else 'your best project'}, then add one line about explaining it to a teammate on your resume.")
    base = projects[0] if projects else "a small project"
    if adj and where:
        return (f"About {days} days: extend {where[0].replace(chr(39), '')} to use {skill} "
                f"(you already know {adj}), then list {skill} on your resume with that link.")
    return f"About {days} days: follow the official {skill} tutorial, then add {skill} to {base} and describe it in one resume bullet."


def analyze(profile: Dict[str,Any], job: Dict[str,Any]) -> Dict[str,Any]:
    candidate=profile_skill_set(profile)
    required=list(dict.fromkeys(job.get("required_skills",[]) or []))
    preferred=list(dict.fromkeys(job.get("preferred_skills",[]) or []))
    critical=[]; partial=[]; demonstrated=[]; preferred_missing=[]
    for s in required:
        state=match_state(candidate,s)
        item=tailored_gap(s,"required",profile,job)
        if state!="missing":
            ev=evidence_for(s,profile)
            if ev: item["why_important"]="Demonstrated in "+" and ".join(ev)+"."
        if state=="missing": critical.append(item)
        elif state=="partial": partial.append(item)
        else: demonstrated.append(item)
    for s in preferred:
        if match_state(candidate,s)=="missing":
            preferred_missing.append(tailored_gap(s,"preferred",profile,job))
    exp_text=norm(job.get("experience_requirements"))
    has_exp=bool(profile.get("experience"))
    experience_gaps=[]
    if exp_text and not any(x in exp_text for x in ("student","fresher","0-1","0-2")) and not has_exp:
        experience_gaps.append({"requirement":job.get("experience_requirements"),"why_important":"The posting specifies prior experience beyond a student/fresher-only requirement."})
    education_gap=[]
    edu_text=norm(" ".join(str(x) for x in profile.get("education",[])))
    req_edu=norm(job.get("education_requirements") or job.get("qualifications"))
    if req_edu and not edu_text:
        education_gap.append({"requirement":job.get("education_requirements") or job.get("qualifications"),"why_important":"Education is explicitly specified in the posting."})
    fallback={
        "summary":f"{len(critical)} required skill gap(s), {len(partial)} partial match(es), and {len(preferred_missing)} preferred skill gap(s) were identified from the available profile data.",
        "critical_missing_skills":critical,"partially_demonstrated_skills":partial,
        "demonstrated_required_skills":demonstrated,"preferred_skill_gaps":preferred_missing,
        "experience_gaps":experience_gaps,"qualification_gaps":education_gap,
        "recommendations":[
            {"gap":x["skill"],"action":tailored_action(x["skill"],profile,job),"priority":"high"}
            for x in critical
        ][:8] + [
            {"gap":x["skill"],"action":tailored_action(x["skill"],profile,job),"priority":"medium"}
            for x in preferred_missing
        ][:4]
    }
    prompt=f"""You are a Skill Gap Analysis Agent. Use ONLY evidence in the candidate profile and the supplied job posting. Never invent skills, projects, experience, qualifications, or achievements.
Candidate:
{profile}
Job:
{job}
Deterministic findings:
{fallback}
Return JSON with exactly: summary, critical_missing_skills, partially_demonstrated_skills, demonstrated_required_skills, preferred_skill_gaps, experience_gaps, qualification_gaps, recommendations.
Each skill item must contain skill and why_important. Recommendations must contain gap, action, priority.
Tailoring rules: (1) why_important must reference the job's own wording or responsibilities; (2) when the candidate already shows the skill, name the exact project or role that proves it; (3) each action must be concrete, name one of the candidate's real projects to extend, and include a time estimate in days; (4) mention adjacent skills the candidate already has. Keep everything realistic for a student and never invent experience."""
    return call_json(
        "You produce evidence-grounded skill-gap analysis for internship applicants. Do not treat a missing profile field as proof that the candidate lacks the capability; call it an unverified gap when appropriate.",
        prompt, fallback
    )

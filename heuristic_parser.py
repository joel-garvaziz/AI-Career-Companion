"""Offline resume parser (no LLM): section + pattern based extraction.

Used as the fallback when no LLM key is configured or the LLM call fails, so
Milestone 1 (upload -> parsed profile) works completely offline.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List

SECTION_ALIASES = {
    "education": ("education", "academic", "academics", "qualification"),
    "skills": ("skills", "technical skills", "core competencies", "skills & tools"),
    "projects": ("projects", "academic projects", "personal projects"),
    "experience": ("experience", "work experience", "internships", "employment", "professional experience"),
    "other": ("certifications", "achievements", "awards", "positions of responsibility", "extracurricular",
              "publications", "interests", "languages", "references", "summary", "objective", "profile"),
}
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_TAIL = re.compile(rf"\s*((?:{MONTH}\s*[-–—�]?\s*)?(?:{MONTH}\s*)?\d{{4}}(?:\s*[-–—�]\s*(?:\d{{4}}|present|{MONTH}\s*\d{{4}}))?|\d{{4}}\s*[-–—�]\s*(?:\d{{4}}|present))\s*$", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){9,11}\d(?!\d)")
DEGREE = re.compile(r"\b(b\.?\s?tech|m\.?\s?tech|b\.?\s?e\b|m\.?\s?e\b|b\.?\s?sc|m\.?\s?sc|bca|mca|bba|mba|bachelor|master|ph\.?d|diploma|b\.?\s?com)[^\n]*", re.I)
BULLET = re.compile(r"^\s*[•●▪■◦\-*•�·]\s*")

KNOWN_SKILLS = {
    "languages": ["Python", "Java", "C", "C++", "C#", "JavaScript", "TypeScript", "SQL", "PL/SQL", "HTML", "CSS", "Go", "Rust", "Kotlin", "Swift", "R", "PHP", "Dart", "Bash", "MATLAB"],
    "frameworks": ["Flask", "Django", "FastAPI", "React", "Angular", "Vue", "Node.js", "Express", "Spring Boot", "Flutter", "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy", "Tailwind", "Bootstrap", "PyQt5"],
    "databases": ["MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis", "Oracle", "Firebase", "SQL Server"],
    "tools": ["Git", "GitHub", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Jira", "VS Code", "Postman", "Figma", "Tableau", "Power BI", "CI/CD", "Jenkins", "LaTeX", "Excel"],
}
SOFT = ["Communication", "Teamwork", "Leadership", "Problem Solving", "Time Management", "Adaptability", "Critical Thinking", "Collaboration"]


def _sections(lines: List[str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {"header": []}
    cur = "header"
    for ln in lines:
        key = re.sub(r"[^a-z& ]", "", ln.strip().lower()).strip()
        found = None
        if key and len(ln.strip()) <= 40:
            for name, aliases in SECTION_ALIASES.items():
                if key in aliases:
                    found = name if name != "other" else f"other:{key}"
                    break
        if found:
            cur = found
            out.setdefault(cur, [])
        else:
            out[cur].append(ln)
    return out


def _split_date(title: str):
    m = DATE_TAIL.search(title)
    if m and m.start() > 0:
        return title[:m.start()].strip(" ,|-–—"), m.group(1).strip()
    return title.strip(), None


def _entries(lines: List[str]) -> List[Dict[str, Any]]:
    """Group lines into entries: title, optional tech line, bullet description."""
    entries: List[Dict[str, Any]] = []
    cur = None
    for raw in lines:
        ln = raw.strip()
        if not ln:
            continue
        if BULLET.match(ln):
            if cur is None:
                continue
            cur["bullets"].append(BULLET.sub("", ln))
            cur["_last_bullet"] = True
        elif cur is not None and ln[0].islower() and cur["bullets"]:
            cur["bullets"][-1] += " " + ln
        elif cur is not None and not cur["bullets"] and not cur.get("sub"):
            cur["sub"] = ln
        else:
            cur = {"title": ln, "sub": None, "bullets": []}
            entries.append(cur)
    return entries


def _skills(lines: List[str], full_text: str) -> Dict[str, List[str]]:
    result = {"technical_skills": [], "soft_skills": [], "tools": [], "programming_languages": [], "frameworks": [], "databases": []}
    mapping = {"language": "programming_languages", "framework": "frameworks", "librar": "frameworks", "database": "databases",
               "tool": "tools", "cloud": "tools", "devops": "tools", "soft": "soft_skills"}

    def add(bucket, item):
        item = item.strip(" .;")
        if item and item.lower() not in {x.lower() for x in result[bucket]} and len(item) < 40:
            result[bucket].append(item)

    for ln in lines:
        if ":" not in ln:
            continue
        label, _, rest = ln.partition(":")
        bucket = next((v for k, v in mapping.items() if k in label.lower()), "technical_skills")
        items = [i for i in re.split(r",|;|\||•|�", rest) if i.strip()]
        if bucket == "technical_skills" and len(items) == 1 and len(items[0]) > 30:
            continue  # prose, not a skill list
        for it in items:
            add(bucket, it)
    # vocabulary scan over the whole resume catches skills outside a SKILLS block
    low = full_text
    for bucket, vocab in KNOWN_SKILLS.items():
        target = "programming_languages" if bucket == "languages" else bucket
        for v in vocab:
            if re.search(rf"(?<![\w+#]){re.escape(v)}(?![\w+#])", low, re.I if len(v) > 2 else 0):
                add(target, v)
    for v in SOFT:
        if re.search(v, full_text, re.I):
            add("soft_skills", v)
    flat = result["programming_languages"] + result["frameworks"] + result["databases"] + result["tools"]
    for it in flat:
        add("technical_skills", it)
    return result


def heuristic_parse(text: str) -> Dict[str, Any]:
    text = text.replace("\r", "")
    lines = [l.rstrip() for l in text.split("\n")]
    sec = _sections(lines)
    header = [l for l in sec["header"] if l.strip()]

    email = EMAIL.search(text)
    phone = PHONE.search(" ".join(header[:6])) or PHONE.search(text)
    linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/[\w\-/%]+", text, re.I)
    github = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", text, re.I)
    name = None
    for l in header[:4]:
        cand = l.strip()
        if EMAIL.search(cand) or re.search(r"\d{3}", cand) or "|" in cand:
            continue
        if 2 <= len(cand.split()) <= 5 and re.fullmatch(r"[A-Za-z .'-]+", cand):
            name = cand.title() if cand.isupper() else cand
            break

    if not name:  # two-column layouts: look further down, then fall back to the LinkedIn / email handle
        skip = {"contact", "summary", "skills", "education", "experience", "projects", "certifications", "profile", "objective"}
        for l in [x.strip() for x in lines if x.strip()][:40]:
            if l.lower() in skip or EMAIL.search(l) or re.search(r"\d", l) or "|" in l:
                continue
            if 2 <= len(l.split()) <= 4 and re.fullmatch(r"[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+){1,3}", l) and l.split()[0].lower() not in {"final", "bachelor", "master", "computer", "software", "data"}:
                name = l
                break
    if not name and linkedin:
        slug = linkedin.group(0).rstrip("/").split("/")[-1]
        words = [w for w in re.split(r"[-_.]+", slug) if w and not w.isdigit()]
        if words:
            name = " ".join(w.capitalize() for w in words)

    education = []
    for e in _entries(sec.get("education", [])):
        title, dates = _split_date(re.sub(r"(?<=[a-z\)])(?=\d{4})", " ", e["title"]))
        block = " ".join([e["sub"] or ""] + e["bullets"])
        dm = DEGREE.search(block) or DEGREE.search(title)
        grade = re.search(r"(?:cgpa|gpa|percentage|grade)[:\s]*([\d.]+\s*(?:/\s*\d+)?%?)", block + " " + title, re.I)
        if DEGREE.match(title) and not e["sub"]:  # degree line first, institution later
            continue
        education.append({
            "degree": dm.group(0).split("CGPA")[0].strip(" ,-") if dm else None,
            "institution": title if not DEGREE.match(title) else None,
            "field_of_study": None,
            "start_date": dates.split("-")[0].strip() if dates and re.search(r"[-–—�]", dates) else None,
            "end_date": re.split(r"[-–—�]", dates)[-1].strip() if dates else None,
            "grade": grade.group(1).strip() if grade else None,
            "description": None,
        })
    if not education:  # e.g. degree and institution on one line
        for ln in sec.get("education", []):
            m = DEGREE.search(ln)
            if m:
                education.append({"degree": m.group(0).strip(), "institution": None, "field_of_study": None,
                                  "start_date": None, "end_date": None, "grade": None, "description": None})
                break
    # attach the degree line that followed an institution entry
    for e in _entries(sec.get("education", [])):
        if e["sub"] and DEGREE.search(e["sub"]) and education:
            education[0]["degree"] = education[0]["degree"] or DEGREE.search(e["sub"]).group(0).split("CGPA")[0].strip()

    def build(section, kind):
        items = []
        for e in _entries(sec.get(section, [])):
            title, dates = _split_date(e["title"])
            desc = " ".join(e["bullets"])[:900] or None
            techs = [t.strip() for t in re.split(r",|;", e["sub"]) if t.strip()] if e["sub"] and "," in e["sub"] else []
            if "|" in title:  # "Project | Tech, Tech" on one line
                title, _, tail = title.partition("|")
                title = title.strip()
                techs = techs or [t.strip() for t in re.split(r",|;", tail) if t.strip()]
            if kind == "project":
                items.append({"project_name": title, "description": desc, "technologies": techs, "github_url": None, "live_url": None, "role": None})
            else:
                sub = e["sub"] or ""
                role = re.sub(r"\(.*?\)", "", sub).strip() or None
                start = end = None
                if dates and re.search(r"[-–—�]", dates):
                    start, end = [p.strip() for p in re.split(r"[-–—�]", dates, 1)]
                else:
                    end = dates
                items.append({"company": title, "job_title": role, "location": None, "start_date": start, "end_date": end,
                              "description": desc, "technologies": techs})
        return items

    parsed = {
        "full_name": name,
        "email": email.group(0) if email else None,
        "phone": re.sub(r"\s+", " ", phone.group(0)).strip() if phone else None,
        "linkedin": linkedin.group(0) if linkedin else None,
        "github": github.group(0) if github else None,
        "portfolio": None,
        "education": education,
        "experience": build("experience", "experience"),
        "projects": build("projects", "project"),
    }
    parsed.update(_skills(sec.get("skills", []), text))
    return parsed

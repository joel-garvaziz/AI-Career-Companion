"""Milestone 1 evaluation: offline resume extraction over the sample PDFs.

Runs the deterministic parser (no LLM) on every distinct sample resume and
reports which profile fields were extracted.  Usage: python evaluate_m1.py
"""
import glob, hashlib, os

os.environ["OPENROUTER_API_KEY"] = ""; os.environ["GEMINI_API_KEY"] = ""; os.environ["GOOGLE_API_KEY"] = ""
from heuristic_parser import heuristic_parse  # noqa: E402
from resume_service import extract_pdf_text  # noqa: E402

FIELDS = ["full_name", "email", "phone", "linkedin", "github", "technical_skills", "education", "experience", "projects"]


def main():
    files = sorted(glob.glob("__DATA__/*.pdf") + glob.glob("uploads/*.pdf"))
    seen, rows = set(), []
    for f in files:
        try:
            text = extract_pdf_text(f)
        except Exception as exc:
            rows.append((os.path.basename(f), None, str(exc)))
            continue
        digest = hashlib.md5(text.encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        parsed = heuristic_parse(text)
        rows.append((os.path.basename(f), {k: bool(parsed.get(k)) for k in FIELDS}, len(parsed["technical_skills"])))
    ok = [r for r in rows if r[1]]
    print(f"Distinct resumes evaluated: {len(ok)}")
    for name, cov, n in ok:
        got = sum(cov.values())
        missing = [k for k, v in cov.items() if not v]
        print(f"  {name[:16]:16} {got}/{len(FIELDS)} fields, {n} skills" + (f"  missing: {', '.join(missing)}" if missing else ""))
    total = sum(sum(c.values()) for _, c, _ in ok) / (len(ok) * len(FIELDS) or 1)
    print(f"Overall field coverage: {total:.0%}")


if __name__ == "__main__":
    main()

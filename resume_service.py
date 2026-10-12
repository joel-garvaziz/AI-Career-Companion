import json
import re
from pathlib import Path
from pypdf import PdfReader
import logging
from resumeparser import ats_extractor
from heuristic_parser import heuristic_parse

logger = logging.getLogger(__name__)


TARGET_KEYS = {
    "full_name", "email", "phone", "linkedin", "github", "portfolio",
    "technical_skills", "soft_skills", "tools", "programming_languages",
    "frameworks", "databases", "education", "experience", "projects"
}


def extract_pdf_text(path):
    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError("The PDF contains no selectable/extractable text.")
    return text


def _clean_json_text(raw):
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise ValueError("Parser returned an unsupported result.")
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def normalize_parsed_data(raw):
    data = _clean_json_text(raw)
    if not isinstance(data, dict):
        raise ValueError("Parser result must be a JSON object.")

    # Preserve known fields and tolerate the original parser's employment naming.
    normalized = {key: data.get(key) for key in TARGET_KEYS}
    normalized["full_name"] = data.get("full_name") or data.get("name")
    normalized["email"] = data.get("email") or data.get("email_id")
    normalized["linkedin"] = data.get("linkedin") or data.get("linkedin_id")
    normalized["github"] = data.get("github") or data.get("github_portfolio")
    normalized["experience"] = data.get("experience") or data.get("employment") or data.get("employment_details") or []
    normalized["education"] = data.get("education") or []
    normalized["projects"] = data.get("projects") or []
    for key in ("technical_skills", "soft_skills", "tools", "programming_languages", "frameworks", "databases"):
        value = normalized.get(key)
        if value is None:
            normalized[key] = []
        elif isinstance(value, str):
            normalized[key] = [x.strip() for x in re.split(r",|;|\n", value) if x.strip()]
        elif not isinstance(value, list):
            normalized[key] = [str(value)]
    for key in ("education", "experience", "projects"):
        if not isinstance(normalized[key], list):
            normalized[key] = []
    return normalized


def parse_resume(path):
    text = extract_pdf_text(path)
    try:
        raw = ats_extractor(text)  # LLM parser (Gemini/OpenRouter) is the primary source.
        data = normalize_parsed_data(raw)
        data["parser"] = "llm"
        return data
    except Exception as exc:  # no key, network error, bad JSON -> offline parser
        logger.warning("LLM resume parsing unavailable, using offline parser: %s", exc)
        data = normalize_parsed_data(heuristic_parse(text))
        data["parser"] = "offline"
        return data

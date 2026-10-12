import os
from openai import OpenAI
from llm_utils import llm_config, llm_available, make_client, note_llm_failure
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_api_key():
    key = llm_config()[0]
    if key:
        return key
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        return data.get("OPENROUTER_API_KEY")
    return None


def ats_extractor(resume_data):
    api_key = _load_api_key()
    if not api_key or not llm_available():
        raise RuntimeError("No LLM API key configured (set GEMINI_API_KEY or OPENROUTER_API_KEY).")

    prompt = """
You are an AI bot designed to act as a professional resume parser.

Extract information from the resume into ONLY valid JSON with this exact top-level schema:
{
  "full_name": null,
  "email": null,
  "phone": null,
  "linkedin": null,
  "github": null,
  "portfolio": null,
  "technical_skills": [],
  "soft_skills": [],
  "tools": [],
  "programming_languages": [],
  "frameworks": [],
  "databases": [],
  "education": [{"degree": null, "institution": null, "field_of_study": null, "start_date": null, "end_date": null, "grade": null, "description": null}],
  "experience": [{"company": null, "job_title": null, "location": null, "start_date": null, "end_date": null, "description": null, "technologies": []}],
  "projects": [{"project_name": null, "description": null, "technologies": [], "github_url": null, "live_url": null, "role": null}]
}
Use null when a scalar field is absent and [] when a list is absent. Never invent information.
Return ONLY JSON. Do not use Markdown fences.
"""

    _, base_url, model = llm_config()
    client = make_client(api_key, base_url or "https://openrouter.ai/api/v1")
    try:
        response = client.chat.completions.create(
            model=model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": resume_data},
            ],
            temperature=0.0,
            max_tokens=int(os.getenv("LLM_PARSE_MAX_TOKENS", "8000")),
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        note_llm_failure(exc)
        raise
    return response.choices[0].message.content

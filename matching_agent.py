"""
Milestone 2.3 — Job-Resume Matching Agent

Combines:
- Milestone 1 structured candidate profile
- Milestone 2 RAG retrieval
- deterministic compatibility scoring
- optional OpenRouter LLM reasoning

The numeric score is calculated using explicit, reproducible rules.
The LLM is used only for natural-language reasoning.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Iterable, List, Set

from dotenv import load_dotenv
from openai import OpenAI

from jobs_dataset import get_all_jobs
from rag_pipeline import get_rag_pipeline

load_dotenv()

logger = logging.getLogger(__name__)


WEIGHTS = {
    "required_skills": 0.40,
    "preferred_skills": 0.15,
    "education": 0.15,
    "experience": 0.10,
    "responsibilities": 0.10,
    "retrieval_similarity": 0.10,
}


def _normalise(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9+#.\- ]+",
        " ",
        str(value).lower()
    ).strip()


def _skill_set(values: Any) -> Set[str]:
    """Convert strings/lists of skills into normalized skill terms."""
    if values is None:
        return set()

    if isinstance(values, str):
        values = re.split(r"[,;\n|]", values)

    result = set()

    for value in values:
        item = _normalise(value)

        if item:
            result.add(item)

    return result


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        return " ".join(str(v) for v in value)

    if isinstance(value, dict):
        return " ".join(str(v) for v in value.values())

    return str(value)


def _candidate_skills(profile: Dict[str, Any]) -> Set[str]:
    values = []

    for key in (
        "skills",
        "technical_skills",
        "programming_languages",
        "tools",
        "frameworks",
        "libraries",
    ):
        value = profile.get(key)

        if isinstance(value, list):
            values.extend(value)

        elif isinstance(value, str):
            values.extend(re.split(r"[,;\n|]", value))

    extracted = profile.get("extracted_data") or profile.get("resume_data")

    if isinstance(extracted, dict):
        for key in (
            "skills",
            "technical_skills",
            "tools",
            "frameworks",
        ):
            value = extracted.get(key)

            if isinstance(value, list):
                values.extend(value)

            elif isinstance(value, str):
                values.extend(re.split(r"[,;\n|]", value))

    return _skill_set(values)


def _skill_match(
    candidate: Set[str],
    job_skills: Any
) -> tuple[float, List[str], List[str]]:

    required = _skill_set(job_skills)

    if not required:
        return 1.0, [], []

    matched = sorted(
        skill
        for skill in required
        if skill in candidate
        or any(
            skill in c or c in skill
            for c in candidate
        )
    )

    missing = sorted(required - set(matched))

    return len(matched) / len(required), matched, missing


def _text_overlap(candidate_text: str, job_text: str) -> float:
    candidate_words = {
        w
        for w in re.findall(
            r"[a-zA-Z][a-zA-Z0-9+#.\-]*",
            _normalise(candidate_text)
        )
        if len(w) > 2
    }

    job_words = {
        w
        for w in re.findall(
            r"[a-zA-Z][a-zA-Z0-9+#.\-]*",
            _normalise(job_text)
        )
        if len(w) > 2
    }

    if not job_words:
        return 0.0

    return len(candidate_words & job_words) / len(job_words)


def _semantic_responsibility_score(
    profile: Dict[str, Any],
    job: Dict[str, Any]
) -> float:

    candidate_text = " ".join(
        [
            _flatten_text(profile.get("projects")),
            _flatten_text(profile.get("experience")),
            _flatten_text(profile.get("skills")),
        ]
    )

    job_text = _flatten_text(job.get("responsibilities"))

    direct_overlap = _text_overlap(candidate_text, job_text)

    candidate_lower = _normalise(candidate_text)
    job_lower = _normalise(job_text)

    concept_groups = {
        "api": ["api", "apis", "rest", "endpoint", "endpoints"],
        "database": ["database", "sql", "query", "queries", "mysql", "postgresql"],
        "backend": ["backend", "server", "service", "services"],
        "frontend": ["frontend", "ui", "interface", "web"],
        "python": ["python"],
        "testing": ["test", "testing", "debug", "debugging"],
        "cloud": ["cloud", "aws", "azure", "gcp"],
        "devops": ["docker", "kubernetes", "ci", "cd", "deployment"],
        "machine_learning": ["machine learning", "ml", "model", "models"],
        "data": ["data", "analytics", "analysis", "pandas", "visualization"],
    }

    matched_concepts = 0
    relevant_concepts = 0

    for terms in concept_groups.values():

        job_has_concept = any(
            term in job_lower
            for term in terms
        )

        if not job_has_concept:
            continue

        relevant_concepts += 1

        if any(
            term in candidate_lower
            for term in terms
        ):
            matched_concepts += 1

    concept_score = (
        matched_concepts / relevant_concepts
        if relevant_concepts
        else 0.0
    )

    return min(
        1.0,
        (direct_overlap * 0.35)
        + (concept_score * 0.65)
    )


def _education_score(
    profile: Dict[str, Any],
    job: Dict[str, Any]
) -> float:

    candidate = _normalise(
        _flatten_text(
            profile.get("education")
            or profile.get("degree")
            or profile.get("qualification")
        )
    )

    required = _normalise(
        job.get("education_requirements")
        or job.get("qualifications")
    )

    if not candidate:
        return 0.5

    if not required:
        return 1.0

    degree_terms = [
        "computer science",
        "computer engineering",
        "information technology",
        "data science",
        "software engineering",
        "electronics",
    ]

    candidate_terms = {
        term
        for term in degree_terms
        if term in candidate
    }

    required_terms = {
        term
        for term in degree_terms
        if term in required
    }

    if candidate_terms & required_terms:
        return 1.0

    if (
        "b.tech" in candidate
        or "b.e" in candidate
        or "bachelor" in candidate
    ):
        if (
            "b.tech" in required
            or "b.e" in required
            or "bachelor" in required
        ):
            return 1.0

    return 0.0


def _experience_score(
    profile: Dict[str, Any],
    job: Dict[str, Any]
) -> float:

    candidate_experience = _normalise(
        _flatten_text(
            profile.get("experience")
            or profile.get("work_experience")
        )
    )

    requirement = _normalise(
        job.get("experience_requirements")
    )

    if (
        "student" in requirement
        or "fresher" in requirement
        or "0-1" in requirement
    ):
        return 1.0

    if not candidate_experience:
        return 0.5

    return (
        1.0
        if _text_overlap(
            candidate_experience,
            requirement
        ) > 0
        else 0.5
    )


def score_candidate_against_job(
    profile: Dict[str, Any],
    job: Dict[str, Any],
    retrieval_similarity: float = 0.0,
) -> Dict[str, Any]:
    """Calculate an explainable compatibility score for one job."""

    candidate_skills = _candidate_skills(profile)

    required_score, matched_required, missing_required = _skill_match(
        candidate_skills,
        job.get("required_skills", [])
    )

    preferred_score, matched_preferred, missing_preferred = _skill_match(
        candidate_skills,
        job.get("preferred_skills", [])
    )

    education_score = _education_score(profile, job)
    experience_score = _experience_score(profile, job)

    responsibility_score = _semantic_responsibility_score(
        profile,
        job
    )

    retrieval_score = max(
        0.0,
        min(1.0, float(retrieval_similarity))
    )

    weighted_score = (
        required_score * WEIGHTS["required_skills"]
        + preferred_score * WEIGHTS["preferred_skills"]
        + education_score * WEIGHTS["education"]
        + experience_score * WEIGHTS["experience"]
        + responsibility_score * WEIGHTS["responsibilities"]
        + retrieval_score * WEIGHTS["retrieval_similarity"]
    )

    score = round(weighted_score * 100, 2)

    if score >= 80:
        recommendation = "Strong Match"

    elif score >= 65:
        recommendation = "Good Match"

    elif score >= 50:
        recommendation = "Moderate Match"

    else:
        recommendation = "Low Match"

    return {
        "job": job,

        # Keep both names for compatibility with existing M2/UI code.
        "score": score,
        "compatibility_score": score,

        "recommendation": recommendation,

        "retrieval_similarity": round(
            retrieval_score,
            4
        ),

        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,

        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,

        "education_score": round(
            education_score * 100,
            2
        ),

        "experience_score": round(
            experience_score * 100,
            2
        ),

        "responsibility_score": round(
            responsibility_score * 100,
            2
        ),

        "score_breakdown": {
            "required_skills": round(
                required_score * 100,
                2
            ),
            "preferred_skills": round(
                preferred_score * 100,
                2
            ),
            "education": round(
                education_score * 100,
                2
            ),
            "experience": round(
                experience_score * 100,
                2
            ),
            "responsibilities": round(
                responsibility_score * 100,
                2
            ),
            "retrieval_similarity": round(
                retrieval_score * 100,
                2
            ),
        },
    }


def _find_jobs_by_ids(
    ids: Iterable[str]
) -> Dict[str, Dict[str, Any]]:

    wanted = set(ids)

    return {
        job["job_id"]: job
        for job in get_all_jobs()
        if job["job_id"] in wanted
    }


def _build_reasoning_prompt(
    profile: Dict[str, Any],
    result: Dict[str, Any]
) -> str:

    job = result["job"]

    return f"""
You are the Job-Resume Matching Agent in an AI Career Companion.

Explain why this candidate matches or does not match the internship. Write directly to the candidate using 'you', in 2-3 friendly sentences of plain everyday language (no jargon, no percentages, no mention of scores, AI or systems).

Do NOT change the supplied numeric score.

CANDIDATE:
{json.dumps(profile, indent=2, default=str)}

JOB:
{json.dumps(job, indent=2, default=str)}

CALCULATED SCORE:
{result["score"]}/100

MATCHED REQUIRED SKILLS:
{result["matched_required_skills"]}

MISSING REQUIRED SKILLS:
{result["missing_required_skills"]}

MATCHED PREFERRED SKILLS:
{result["matched_preferred_skills"]}

MISSING PREFERRED SKILLS:
{result["missing_preferred_skills"]}

Return valid JSON with exactly these keys:

summary
strengths
skill_gaps
recommendation

Use concise strings/lists.
Do not invent candidate experience.
"""


def _plain_summary(result: Dict[str, Any]) -> str:
    """Friendly, second-person summary built from the match data (no jargon)."""
    have = result.get("matched_required_skills") or []
    miss = result.get("missing_required_skills") or []
    total = len(have) + len(miss)
    title = (result.get("job") or {}).get("job_title", "this internship")
    if total:
        text = f"You already have {len(have)} of the {total} skills this {title} role asks for"
        text += f" ({', '.join(have[:4])})." if have else "."
    else:
        text = f"This {title} role is open to your background."
    if miss:
        text += f" To strengthen your application, focus on {', '.join(miss[:3])}."
    else:
        text += " You meet all of the main requirements - a strong candidate."
    return text


def _llm_reasoning(
    profile: Dict[str, Any],
    result: Dict[str, Any]
) -> Dict[str, Any]:

    from llm_utils import llm_config, llm_available, make_client, note_llm_failure
    api_key, base_url, model = llm_config()

    if not api_key or not llm_available():
        return {
            "summary": _plain_summary(result),
            "strengths": result["matched_required_skills"],
            "skill_gaps": result["missing_required_skills"],
            "recommendation": result["recommendation"],
        }

    client = make_client(api_key, base_url)

    try:

        response = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1200")),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You provide concise, evidence-based "
                        "career matching explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": _build_reasoning_prompt(
                        profile,
                        result
                    ),
                },
            ],
        )

        content = (
            response.choices[0].message.content
            or ""
        )

        content = re.sub(
            r"^```json\s*|\s*```$",
            "",
            content.strip()
        )

        parsed = json.loads(content)

        return {
            "summary": parsed.get(
                "summary",
                ""
            ),
            "strengths": parsed.get(
                "strengths",
                []
            ),
            "skill_gaps": parsed.get(
                "skill_gaps",
                []
            ),
            "recommendation": parsed.get(
                "recommendation",
                result["recommendation"]
            ),
        }

    except Exception as exc:

        note_llm_failure(exc)
        logger.warning("LLM reasoning unavailable, using rule-based fallback: %s", str(exc)[:160])

        return {
            "summary": _plain_summary(result),
            "strengths": result["matched_required_skills"],
            "skill_gaps": result["missing_required_skills"],
            "recommendation": result["recommendation"],
        }


def match_profile(
    profile: Dict[str, Any],
    query: str | None = None,
    top_k_retrieval: int = 15,
    top_k_results: int = 10,
    include_llm_reasoning: bool = True,
) -> List[Dict[str, Any]]:

    """
    Retrieve jobs and rank them against the candidate profile.

    If no query is provided, a search query is automatically created
    from the candidate's skills, education, experience and projects.
    """

    if not query:

        query = " ".join(
            [
                _flatten_text(
                    profile.get("skills")
                ),
                _flatten_text(
                    profile.get("education")
                ),
                _flatten_text(
                    profile.get("experience")
                ),
                _flatten_text(
                    profile.get("projects")
                ),
            ]
        ).strip()

    if not query:
        query = (
            "computer science "
            "software engineering internship"
        )

    retrieval = get_rag_pipeline().search(
        query,
        top_k=top_k_retrieval
    )

    jobs = _find_jobs_by_ids(
        item["job_id"]
        for item in retrieval
    )

    retrieval_scores = {
        item["job_id"]: item["similarity"]
        for item in retrieval
    }

    results = []

    for job_id, job in jobs.items():

        result = score_candidate_against_job(
            profile,
            job,
            retrieval_similarity=retrieval_scores.get(
                job_id,
                0.0
            ),
        )

        results.append(result)

    results.sort(
        key=lambda item: (
            item["score"],
            item["retrieval_similarity"],
        ),
        reverse=True,
    )

    if not include_llm_reasoning:
        for result in results:
            result["reasoning"] = {
                "summary": _plain_summary(result),
                "strengths": result["matched_required_skills"],
                "skill_gaps": result["missing_required_skills"],
                "recommendation": result["recommendation"],
            }
    else:
        # LLM explanations only for the best candidates: keeps latency and API quota bounded.
        top_n = int(os.getenv("LLM_REASONING_TOP_N", "3"))
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=max(1, top_n)) as pool:
            futures = {i: pool.submit(_llm_reasoning, profile, results[i]) for i in range(min(top_n, len(results)))}
        for i, result in enumerate(results):
            if i in futures:
                result["reasoning"] = futures[i].result()
            else:
                result["reasoning"] = {
                    "summary": _plain_summary(result),
                    "strengths": result["matched_required_skills"],
                    "skill_gaps": result["missing_required_skills"],
                    "recommendation": result["recommendation"],
                }

    # Remove duplicate recommendations based on the same
    # job title + company + location combination.
    unique_results = []
    seen_jobs = set()

    for result in results:
        job = result["job"]

        job_key = (
            _normalise(job.get("job_title")),
            _normalise(job.get("company")),
            _normalise(job.get("location")),
        )

        if job_key in seen_jobs:
            continue

        seen_jobs.add(job_key)
        unique_results.append(result)

        if len(unique_results) >= top_k_results:
            break

    return unique_results


if __name__ == "__main__":

    sample_profile = {
        "skills": [
            "Python",
            "Flask",
            "SQL",
            "Git",
            "Docker"
        ],
        "education": "B.Tech Computer Science",
        "experience": "Student developer",
        "projects": (
            "Flask employee management application "
            "and machine learning projects"
        ),
    }

    matches = match_profile(
        sample_profile,
        query=(
            "Python backend internship "
            "with SQL Flask Docker"
        ),
        top_k_results=5,
        include_llm_reasoning=False,
    )

    for index, result in enumerate(
        matches,
        start=1
    ):

        print(
            f"{index}. "
            f"{result['job']['job_title']} - "
            f"{result['job']['company']} - "
            f"{result['score']}/100 - "
            f"{result['recommendation']}"
        )
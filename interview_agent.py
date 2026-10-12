"""Milestone 3.3 — Interview Preparation Agent."""
from __future__ import annotations

from typing import Any, Dict

from llm_utils import call_json


def build_fallback(profile: Dict[str, Any], job: Dict[str, Any], gaps: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic fallback so M3.3 still works when the LLM is unavailable."""
    required = list(job.get("required_skills", []) or [])[:8]
    preferred = list(job.get("preferred_skills", []) or [])[:5]
    projects = list(profile.get("projects", []) or [])[:4]

    questions = []

    # Technical questions from required skills.
    for skill in required:
        questions.append(
            {
                "type": "technical",
                "question": f"How would you use {skill} in a practical project?",
                "why": "It is listed as a required skill for the selected role.",
                "preparation_guidance": (
                    f"Review the fundamentals of {skill}, common use cases, "
                    "trade-offs, and be ready to explain one genuine example."
                ),
            }
        )

    # Role-specific questions from responsibilities.
    responsibilities = str(job.get("responsibilities", "")).strip()
    if responsibilities:
        questions.append(
            {
                "type": "role-specific",
                "question": "Which responsibility in this internship would you be most prepared to handle, and why?",
                "why": "The answer should connect the candidate's verified profile to the role responsibilities.",
                "preparation_guidance": (
                    "Choose one responsibility and connect it to an actual skill, "
                    "project, coursework, or experience in your profile."
                ),
            }
        )

    # Project questions from the candidate's actual projects.
    for project in projects:
        project_name = project.get("project_name", "your project")
        questions.append(
            {
                "type": "project",
                "question": f"Explain your project '{project_name}' and the technical decisions you made.",
                "why": "This project is present in the candidate profile.",
                "preparation_guidance": (
                    "Prepare the problem, your approach, architecture, individual contribution, "
                    "technical challenges, testing, and actual results."
                ),
            }
        )

    # Resume/HR questions.
    questions.extend(
        [
            {
                "type": "resume",
                "question": "Walk me through your background and the experience most relevant to this internship.",
                "why": "This is a common resume-based interview question.",
                "preparation_guidance": (
                    "Give a concise chronological summary and focus on evidence that is relevant to the selected role."
                ),
            },
            {
                "type": "HR/general",
                "question": "Why are you interested in this internship?",
                "why": "Internship interviews commonly test motivation and role fit.",
                "preparation_guidance": (
                    "Connect your genuine interests, current skills, projects, and learning goals to the role."
                ),
            },
            {
                "type": "HR/general",
                "question": "Tell me about a challenge you faced in a project and how you handled it.",
                "why": "This evaluates problem solving and communication.",
                "preparation_guidance": "Use a real example and structure it with Situation, Task, Action, and Result.",
            },
        ]
    )

    # Add preferred-skill questions without claiming the candidate has them.
    for skill in preferred:
        questions.append(
            {
                "type": "role-specific",
                "question": f"What is your current familiarity with {skill}?",
                "why": "It is listed as a preferred skill for the selected role.",
                "preparation_guidance": (
                    f"Be honest about your current level. If you have not used {skill}, "
                    "explain what related concepts you do know and how you would learn it."
                ),
            }
        )

    # Prioritize revision topics using required skills and verified gaps.
    revision_topics = []
    for item in required:
        if item not in revision_topics:
            revision_topics.append(item)

    for item in gaps.get("critical_missing_skills", []) or []:
        skill = item.get("skill") if isinstance(item, dict) else str(item)
        if skill and skill not in revision_topics:
            revision_topics.append(skill)

    for item in gaps.get("partially_demonstrated_skills", []) or []:
        skill = item.get("skill") if isinstance(item, dict) else str(item)
        if skill and skill not in revision_topics:
            revision_topics.append(skill)

    return {
        "questions": questions[:20],
        "revision_topics": revision_topics[:12],
        "preparation_plan": [
            "Review the required skills and be able to explain practical examples.",
            "Prepare concise explanations of your projects and your individual contribution.",
            "Review the role responsibilities and connect them only to demonstrated experience.",
            "Revise the identified skill gaps before the interview.",
            "Practice concise STAR-style answers for behavioral questions.",
        ],
        "mock_interview_available": True,
    }


def prepare(profile: Dict[str, Any], job: Dict[str, Any], gaps: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a role-specific interview pack."""
    fallback_result = build_fallback(profile, job, gaps)

    prompt = f"""
Generate a role-specific internship interview preparation pack.

Use ONLY the supplied candidate profile, job posting, and skill-gap analysis.
Never invent candidate experience, projects, certifications, metrics, employers,
dates, achievements, or technologies.

Candidate profile:
{profile}

Job posting:
{job}

Skill-gap analysis:
{gaps}

Return JSON with exactly these keys:
questions, revision_topics, preparation_plan, mock_interview_available

Each question must contain:
type, question, why, preparation_guidance

Include all of these categories when evidence allows:
- technical
- resume
- project
- role-specific
- HR/general

Revision topics should prioritize required skills and verified skill gaps.
"""

    return _clean_prep(call_json(
        "You are an evidence-grounded interview preparation agent for internship applicants.",
        prompt,
        fallback_result,
    ))


def _flat(item):
    """Turn any AI-returned value (string / dict / list) into readable plain text."""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        head = item.get("day") or item.get("when") or item.get("title") or item.get("step") or item.get("topic") or ""
        rest = [v for k, v in item.items() if v and k not in ("day", "when", "title", "step", "topic")]
        head = str(head).strip()
        body = "; ".join(_flat(v) if isinstance(v, (dict, list)) else str(v) for v in rest)
        return f"{head}: {body}" if head and body else (head or body)
    if isinstance(item, (list, tuple)):
        return "; ".join(_flat(x) for x in item)
    return str(item)


def _clean_prep(result):
    if isinstance(result, dict):
        for key in ("revision_topics", "preparation_plan"):
            value = result.get(key)
            if isinstance(value, list):
                items = value
            elif isinstance(value, (str, dict)):
                items = [value]
            else:
                items = []
            result[key] = [t for t in (_flat(x) for x in items) if t]
        if not isinstance(result.get("questions"), list):
            result["questions"] = []
    return result


def evaluate_answer(
    question: str,
    answer: str,
    profile: Dict[str, Any],
    job: Dict[str, Any],
) -> Dict[str, Any]:
    """Evaluate a mock-interview answer."""
    lowered = answer.lower()
    word_count = len(answer.split())
    required = [str(s) for s in (job.get("required_skills") or [])]
    mentioned = [s for s in required if s.lower() in lowered]
    heuristic_score = min(100, 20 + min(word_count, 150) // 3 + 8 * len(mentioned))

    strengths = []
    if word_count >= 60:
        strengths.append("Sufficient depth: the answer develops the point instead of staying generic.")
    if mentioned:
        strengths.append("Mentions role-relevant skills: " + ", ".join(mentioned[:5]) + ".")
    if not strengths:
        strengths.append("Answer submitted for review.")

    improvements = []
    if word_count < 60:
        improvements.append("Expand the answer with a concrete example (aim for 80-150 words).")
    missing = [s for s in required if s.lower() not in lowered]
    if missing:
        improvements.append("Where true for you, connect the answer to: " + ", ".join(missing[:4]) + ".")
    improvements.append("Structure it as situation, action, result, and avoid unsupported claims.")

    fallback_result = {
        "score": heuristic_score,
        "strengths": strengths,
        "improvements": improvements,
        "model_answer_outline": [
            "Context",
            "Your action",
            "Technical reasoning",
            "Outcome",
            "What you learned",
        ],
    }

    prompt = f"""
Evaluate this interview answer without inventing facts.

Question:
{question}

Answer:
{answer}

Candidate profile:
{profile}

Job:
{job}

Return JSON exactly:
score, strengths, improvements, model_answer_outline

Score the answer as an integer from 0 to 100 using clarity, relevance, technical correctness,
and evidence. Do not award credit for claims that are unsupported by the profile.
"""

    result = call_json(
        "You provide constructive, evidence-grounded interview feedback.",
        prompt,
        fallback_result,
    )

    try:
        score = float(result.get("score"))
        if score <= 10:
            score *= 10
        result["score"] = int(max(0, min(100, round(score))))
    except (TypeError, ValueError):
        result["score"] = fallback_result["score"]
    return result

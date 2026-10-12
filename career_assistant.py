"""Milestone 3.4 — Conversational Career Assistant orchestration."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from llm_utils import call_json
from matching_agent import match_profile
from skill_gap_agent import analyze as analyze_gaps
from application_agent import customize
from interview_agent import prepare


def detect_intent(message: str) -> str:
    """Lightweight deterministic routing before the LLM response layer."""
    text = str(message or "").lower()

    if any(
        phrase in text
        for phrase in (
            "interview",
            "mock interview",
            "interview question",
            "prepare me",
            "prepare for",
        )
    ):
        return "interview"

    if any(
        phrase in text
        for phrase in (
            "resume",
            "cv",
            "cover letter",
            "application",
            "tailor",
            "customize",
            "bullet point",
        )
    ):
        return "application"

    if any(
        phrase in text
        for phrase in (
            "skill gap",
            "skills am i missing",
            "skills do i need",
            "what should i improve",
            "what should i learn",
            "improve for this role",
            "missing skill",
            "qualification gap",
        )
    ):
        return "skill_gap"

    if any(
        phrase in text
        for phrase in (
            "compare",
            "which internship",
            "which role",
            "find internship",
            "find internships",
            "suitable internship",
            "suitable internships",
            "match",
            "matches my profile",
        )
    ):
        return "matching"

    return "general"


def _txt(x: Any) -> str:
    if isinstance(x, dict):
        return str(x.get("skill") or x.get("name") or x.get("question") or x.get("topic") or x.get("action") or next(iter(x.values()), ""))
    return str(x)


def fallback_answer(profile: Dict[str, Any], jobs: List[Dict[str, Any]], message: str, tools: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic, grounded reply built from tool output when no LLM is available."""
    name = (profile.get("full_name") or "").split(" ")[0] or "there"
    job = jobs[0] if jobs else {}
    lines: List[str] = []
    refs: List[str] = []
    gap = tools.get("skill_gap")
    title = f"{job.get('job_title')} at {job.get('company')}" if job.get("job_title") else "this role"

    if tools.get("matches"):
        lines.append(f"Hi {name}, here are the internships that fit your profile best right now:")
        for i, m in enumerate(tools["matches"][:5], 1):
            j = m.get("job", {})
            refs.append(str(j.get("job_id", "")))
            miss = ", ".join(_txt(x) for x in m.get("missing_required_skills", [])[:3]) or "no major gaps"
            lines.append(f"{i}. {j.get('job_title')} at {j.get('company')} ({j.get('location')}) - {m.get('score', 0):.0f}% match. To close: {miss}.")
        lines.append("Open a role in the selector above and ask me for a skill-gap analysis, a tailored resume or interview prep.")
    elif tools.get("application"):
        app_ = tools["application"]
        lines.append(f"I've prepared application material for {title}.")
        letter = app_.get("cover_letter")
        if letter:
            lines.append("Cover letter draft:\n" + str(letter)[:900])
        for b in (app_.get("resume_bullets") or app_.get("tailored_resume_points") or [])[:5]:
            lines.append("- " + _txt(b))
        lines.append("Use the Tailored resume / Cover letter agents above to edit, download and save it to your tracker.")
    elif tools.get("interview"):
        iv = tools["interview"]
        lines.append(f"Here is how to prepare for {title}:")
        for q in (iv.get("questions") or [])[:5]:
            lines.append("- " + _txt(q))
        for t in (iv.get("preparation_plan") or [])[:4]:
            lines.append("- Plan: " + _txt(t))
        lines.append("Start the mock interview above to get each answer scored out of 100.")
    elif gap:
        lines.append(f"Skill-gap review for {title}: {gap.get('summary', '')}")
        strong = [_txt(x) for x in gap.get("demonstrated_required_skills", [])]
        if strong:
            lines.append("You already show: " + ", ".join(strong[:8]) + ".")
        miss = [_txt(x) for x in gap.get("critical_missing_skills", [])]
        if miss:
            lines.append("Priority gaps: " + ", ".join(miss[:6]) + ".")
        for r in (gap.get("recommendations") or [])[:4]:
            lines.append(f"- {_txt(r.get('gap'))}: {r.get('action')}" if isinstance(r, dict) else "- " + str(r))
    else:
        top = ", ".join(_txt(x) for x in (profile.get("skills") or profile.get("technical_skills") or [])[:6]) if isinstance(profile, dict) else ""
        lines.append(f"Hi {name}! I can help you find internships, analyse skill gaps, tailor your resume and cover letter, and rehearse interviews.")
        if top:
            lines.append(f"Your profile currently highlights: {top}.")
        lines.append("Try: 'Find internships for me', or pick a role above and ask 'What skills am I missing?'")
    return {"answer": "\n".join(lines), "actions": [], "referenced_job_ids": [r for r in refs if r], "needs_job_selection": False}


def answer(
    profile: Dict[str, Any],
    jobs: List[Dict[str, Any]],
    history: List[Dict[str, str]],
    message: str,
    tool_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Generate the final conversational answer from grounded tool context."""
    context = {
        "recent_conversation": history[-8:],
        "candidate": profile,
        "available_jobs": jobs[:20],
    }

    prompt = f"""
You are the Career Assistant inside an AI Career Companion.

Give personalized, factual, actionable career guidance.
Use ONLY the candidate profile, job data, conversation context, and tool outputs.
Never invent candidate achievements, skills, projects, certifications, metrics,
employers, dates, or experience.

User question:
{message}

Context:
{json.dumps(context, default=str)}

Return JSON exactly:
{{
  "answer": "...",
  "actions": [],
  "referenced_job_ids": [],
  "needs_job_selection": false
}}

If the user asks about a selected role, directly use the relevant tool output.
If information is missing, explicitly say what is unknown.

Make the answer PERSONAL, not a restatement of the tool output:
- Address the candidate by first name and speak to them directly ("you").
- Open with a one-line verdict on their fit for the role (e.g. how many required skills they already show).
- Name their real projects, roles and skills as evidence ("your CineReview project already uses Flask + MySQL").
- Give a short prioritised plan: each step names the skill, one of THEIR projects to extend, and a time estimate in days.
- Suggest one resume bullet or talking point that only restates facts already in their profile (real project names, technologies, results). If the skill is not yet evidenced, phrase it as a template to fill in AFTER they do the step, e.g. 'Built <feature> in <project> using <skill> (<result>)' - never claim something they have not done.
- Use only their first name (the first word of full_name).
- Keep it under 220 words, plain text with short lines; end with one specific next step (e.g. "Run the Application customizer for this role").
- Never mention that you were given "tool outputs" or a "skill gap analysis"; just give the advice.
"""

    return call_json(
        "You are a conversational career assistant that coordinates matching, skill-gap analysis, application customization, and interview preparation. Do not make unsupported claims.",
        prompt,
        fallback_answer(profile, jobs, message.split("\n\nSYSTEM TOOL OUTPUTS")[0], tool_context or {}),
    )


def build_tool_context(
    profile: Dict[str, Any],
    query: str | None = None,
    job: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run only the M2/M3 tools relevant to the user's request."""
    tools: Dict[str, Any] = {}
    intent = detect_intent(query or "")

    # No selected job: use M2 matching for internship-search questions.
    if query and job is None:
        if intent == "matching" or intent == "general":
            try:
                tools["matches"] = match_profile(
                    profile,
                    query=query,
                    top_k_retrieval=15,
                    top_k_results=5,
                    include_llm_reasoning=False,
                )
            except Exception as exc:
                tools["matching_error"] = str(exc)

        return tools

    if job is None:
        return tools

    # Selected role: route to the appropriate M3 agent.
    if intent == "skill_gap":
        try:
            tools["skill_gap"] = analyze_gaps(profile, job)
        except Exception as exc:
            tools["skill_gap_error"] = str(exc)

    elif intent == "application":
        try:
            tools["application"] = customize(profile, job)
        except Exception as exc:
            tools["application_error"] = str(exc)

    elif intent == "interview":
        try:
            gaps = analyze_gaps(profile, job)
            tools["skill_gap"] = gaps
            tools["interview"] = prepare(profile, job, gaps)
        except Exception as exc:
            tools["interview_error"] = str(exc)

    elif intent == "matching":
        # A selected role can still be compared against the candidate.
        try:
            tools["skill_gap"] = analyze_gaps(profile, job)
        except Exception as exc:
            tools["skill_gap_error"] = str(exc)

    else:
        # General role questions default to the most useful evidence source:
        # skill-gap analysis. This keeps the assistant fast and avoids invoking
        # all three expensive agents for every chat message.
        try:
            tools["skill_gap"] = analyze_gaps(profile, job)
        except Exception as exc:
            tools["skill_gap_error"] = str(exc)

    return tools

"""
Milestone 2.4 — Retrieval and Matching Evaluation

Run:
    python evaluate_m2.py

The benchmark uses five synthetic student profiles with deliberately different
technical strengths. Expected job domains are defined manually, then compared
with RAG retrieval and matching-agent rankings.

Metrics:
- Hit@5: expected domain appears in top 5 retrieved jobs
- MRR: reciprocal rank of first expected-domain retrieval
- Matching Hit@5: expected domain appears in top 5 final matches
- Score consistency: average spread of scores across clearly different
  candidate/job combinations

These are development/benchmark metrics, not claims about production accuracy.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Tuple

from jobs_dataset import get_all_jobs
from matching_agent import match_profile
from rag_pipeline import get_rag_pipeline


STUDENT_PROFILES = [
    {
        "name": "Python Backend Student",
        "query": "Python backend internship Flask SQL Docker REST APIs",
        "profile": {
            "skills": ["Python", "Flask", "SQL", "Git", "Docker"],
            "education": "B.Tech Computer Science",
            "experience": "Student developer",
            "projects": "Flask backend application and SQL database project",
        },
        "expected_domains": {"Python Backend", "Full Stack Developer"},
    },
    {
        "name": "Data Analytics Student",
        "query": "data analyst internship Python SQL Excel Power BI data analysis",
        "profile": {
            "skills": ["Python", "SQL", "Excel", "Data Analysis", "Pandas"],
            "education": "B.Tech Computer Science",
            "experience": "Student data analyst",
            "projects": "Sales data analysis and dashboard project",
        },
        "expected_domains": {"Data Analyst"},
    },
    {
        "name": "Machine Learning Student",
        "query": "machine learning internship Python NumPy Pandas scikit-learn TensorFlow",
        "profile": {
            "skills": ["Python", "Machine Learning", "NumPy", "Pandas", "scikit-learn"],
            "education": "B.Tech Computer Science",
            "experience": "Student machine learning developer",
            "projects": "Image classification and machine learning prediction projects",
        },
        "expected_domains": {"Machine Learning"},
    },
    {
        "name": "Frontend Student",
        "query": "frontend web development internship HTML CSS JavaScript React",
        "profile": {
            "skills": ["HTML", "CSS", "JavaScript", "Git", "React"],
            "education": "B.Tech Computer Science",
            "experience": "Student web developer",
            "projects": "Responsive portfolio and JavaScript web application",
        },
        "expected_domains": {"Frontend Developer", "Full Stack Developer"},
    },
    {
        "name": "DevOps Student",
        "query": "DevOps cloud internship Linux Git Docker AWS CI/CD",
        "profile": {
            "skills": ["Linux", "Git", "Python", "Docker", "AWS", "CI/CD"],
            "education": "B.Tech Computer Science",
            "experience": "Student DevOps engineer",
            "projects": "Dockerized Flask application and CI/CD deployment project",
        },
        "expected_domains": {"Cloud/DevOps"},
    },
]


def domain_from_title(title: str) -> str:
    return title.replace(" Intern", "").strip()


def reciprocal_rank(domains: set[str], jobs: List[dict]) -> float:
    for rank, job in enumerate(jobs, start=1):
        domain = domain_from_title(job["job_title"])
        if domain in domains:
            return 1.0 / rank
    return 0.0


def hit_at_k(domains: set[str], jobs: List[dict], k: int = 5) -> int:
    top = jobs[:k]
    return int(
        any(domain_from_title(job["job_title"]) in domains for job in top)
    )


def evaluate():
    rag = get_rag_pipeline()

    retrieval_hits = []
    retrieval_mrr = []
    matching_hits = []
    all_scores = []

    print("=" * 72)
    print("AI CAREER COMPANION — MILESTONE 2.4 EVALUATION")
    print("=" * 72)

    for student in STUDENT_PROFILES:
        print(f"\n{student['name']}")

        retrieved = rag.search(student["query"], top_k=10)

        # Convert retrieved IDs back to complete jobs.
        jobs_by_id = {
            job["job_id"]: job
            for job in get_all_jobs()
        }
        retrieved_jobs = [
            jobs_by_id[item["job_id"]]
            for item in retrieved
            if item["job_id"] in jobs_by_id
        ]

        r_hit = hit_at_k(student["expected_domains"], retrieved_jobs, 5)
        r_mrr = reciprocal_rank(student["expected_domains"], retrieved_jobs)

        matches = match_profile(
            student["profile"],
            query=student["query"],
            top_k_retrieval=15,
            top_k_results=10,
            include_llm_reasoning=False,
        )

        matching_jobs = [result["job"] for result in matches]
        m_hit = hit_at_k(student["expected_domains"], matching_jobs, 5)

        retrieval_hits.append(r_hit)
        retrieval_mrr.append(r_mrr)
        matching_hits.append(m_hit)
        all_scores.extend(result["score"] for result in matches)

        print(f"  Retrieval Hit@5    : {r_hit}")
        print(f"  Retrieval MRR      : {r_mrr:.3f}")
        print(f"  Matching Hit@5     : {m_hit}")
        print("  Top matches:")

        for rank, result in enumerate(matches[:5], start=1):
            print(
                f"    {rank}. {result['job']['job_title']} | "
                f"{result['job']['company']} | "
                f"{result['score']:.2f}/100"
            )

    retrieval_hit_rate = statistics.mean(retrieval_hits) * 100
    mrr = statistics.mean(retrieval_mrr)
    matching_hit_rate = statistics.mean(matching_hits) * 100

    # A spread is useful as a simple consistency indicator:
    # candidates should not receive nearly identical scores for all jobs.
    score_spread = statistics.pstdev(all_scores) if all_scores else 0.0

    print("\n" + "=" * 72)
    print("AGGREGATE RESULTS")
    print("=" * 72)
    print(f"Students evaluated       : {len(STUDENT_PROFILES)}")
    print(f"Retrieval Hit@5          : {retrieval_hit_rate:.2f}%")
    print(f"Mean Reciprocal Rank     : {mrr:.3f}")
    print(f"Matching Hit@5           : {matching_hit_rate:.2f}%")
    print(f"Score standard deviation : {score_spread:.2f}")
    print("\nInterpretation:")
    print("- Higher Hit@5 means relevant domains appear in the top five.")
    print("- Higher MRR means relevant jobs appear closer to rank 1.")
    print("- Matching Hit@5 measures whether the final ranking preserves relevance.")
    print("- Score spread is descriptive; it is not an accuracy metric.")


if __name__ == "__main__":
    evaluate()

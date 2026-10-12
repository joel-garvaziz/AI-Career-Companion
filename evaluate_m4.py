"""M4.3 — performance and resource benchmark.

Measures retrieval latency, deterministic matching time, agent (fallback-path)
latency, prompt size / estimated token usage and process memory.

    python evaluate_m4.py
"""
import json
import os
import statistics
import time

os.environ["OPENROUTER_API_KEY"] = ""; os.environ["GEMINI_API_KEY"] = ""; os.environ["GOOGLE_API_KEY"] = ""  # benchmark the deterministic path only

from jobs_dataset import dataset_quality_report, get_job  # noqa: E402
from rag_pipeline import get_rag_pipeline, semantic_search  # noqa: E402
from matching_agent import match_profile  # noqa: E402
from skill_gap_agent import analyze  # noqa: E402
from application_agent import customize  # noqa: E402
from interview_agent import prepare  # noqa: E402

QUERIES = [
    "python backend flask api", "machine learning pytorch", "data analysis sql dashboards",
    "react frontend developer", "cloud devops docker kubernetes", "cybersecurity network security",
    "flutter mobile app", "nlp transformers", "full stack javascript node", "database sql administration",
]
PROFILE = {
    "full_name": "Benchmark Student",
    "skills": ["Python", "Flask", "SQL", "Git", "Docker", "REST APIs"],
    "education": [{"degree": "B.Tech", "field_of_study": "Computer Science"}],
    "experience": [], "projects": [{"project_name": "Task API", "description": "Flask REST API", "technologies": ["Flask", "SQL"]}],
}


def timed(fn, repeat=5):
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return {"mean_ms": round(statistics.mean(samples), 1), "p95_ms": round(sorted(samples)[int(len(samples) * .95) - 1], 1)}


def memory_mb():
    try:
        import psutil
        return round(psutil.Process().memory_info().rss / 1e6, 1)
    except ImportError:
        return None


def main():
    report = {"dataset": dataset_quality_report()}

    start = time.perf_counter()
    pipeline = get_rag_pipeline()
    pipeline.ensure_index()
    semantic_search("warm-up query", top_k=1)
    report["cold_start_s"] = round(time.perf_counter() - start, 2)

    report["retrieval_top5"] = timed(lambda: [semantic_search(q, top_k=5) for q in QUERIES], repeat=3)
    report["retrieval_per_query_ms"] = round(report["retrieval_top5"]["mean_ms"] / len(QUERIES), 1)

    report["matching_top10_no_llm"] = timed(lambda: match_profile(PROFILE, top_k_retrieval=30, top_k_results=10, include_llm_reasoning=False))

    job = get_job("INT-001")
    gap = analyze(PROFILE, job)
    report["skill_gap"] = timed(lambda: analyze(PROFILE, job))
    report["application_tailoring"] = timed(lambda: customize(PROFILE, job))
    report["interview_prep"] = timed(lambda: prepare(PROFILE, job, gap))

    prompt = json.dumps({"profile": PROFILE, "job": job, "gap": gap}, default=str)
    report["prompt_chars"] = len(prompt)
    report["estimated_prompt_tokens"] = len(prompt) // 4
    report["index_files_mb"] = round(sum(os.path.getsize(os.path.join("rag_index", f)) for f in os.listdir("rag_index")) / 1e6, 2)
    report["process_memory_mb"] = memory_mb()

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""
Milestone 2.2 — RAG Pipeline

Responsibilities:
1. Load the structured internship dataset.
2. Convert each job into meaningful retrieval chunks.
3. Generate semantic embeddings with Sentence Transformers.
4. Persist the local vector index.
5. Perform cosine-similarity semantic search.

The index is stored locally so the model does not need to be re-embedded
on every application start.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer

from jobs_dataset import get_all_jobs


BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "rag_index"
EMBEDDINGS_FILE = INDEX_DIR / "job_embeddings.npy"
METADATA_FILE = INDEX_DIR / "job_chunks.json"

MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",
)


class RAGPipeline:
    """Chunk, embed, index, and semantically retrieve internship postings."""

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None

    @staticmethod
    def chunk_job(job: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split a job into semantically meaningful sections.

        Keeping sections separate improves retrieval because a query about
        skills can match a skills chunk instead of depending on the entire
        job posting being represented as one vector.
        """
        sections = [
            (
                "overview",
                f"""
Job title: {job.get('job_title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Domain: {job.get('domain', '')}
Job type: {job.get('job_type', '')}
Duration: {job.get('duration', '')}
Description: {job.get('job_description', '')}
""",
            ),
            (
                "responsibilities",
                f"""
Job title: {job.get('job_title', '')}
Company: {job.get('company', '')}
Responsibilities:
{job.get('responsibilities', '')}
""",
            ),
            (
                "required_skills",
                f"""
Job title: {job.get('job_title', '')}
Required skills:
{', '.join(job.get('required_skills', []))}
""",
            ),
            (
                "preferred_skills",
                f"""
Job title: {job.get('job_title', '')}
Preferred skills:
{', '.join(job.get('preferred_skills', []))}
""",
            ),
            (
                "qualifications",
                f"""
Job title: {job.get('job_title', '')}
Qualifications: {job.get('qualifications', '')}
Education requirements: {job.get('education_requirements', '')}
Experience requirements: {job.get('experience_requirements', '')}
""",
            ),
        ]

        result = []
        for section_name, text in sections:
            result.append(
                {
                    "chunk_id": f"{job['job_id']}-{section_name}",
                    "job_id": job["job_id"],
                    "section": section_name,
                    "text": " ".join(text.split()),
                }
            )
        return result

    def build_index(self, jobs: List[Dict[str, Any]] | None = None) -> Dict[str, int]:
        """Build and persist the complete local vector index."""
        jobs = jobs or get_all_jobs()

        self.chunks = []
        for job in jobs:
            self.chunks.extend(self.chunk_job(job))

        texts = [chunk["text"] for chunk in self.chunks]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        ).astype(np.float32)

        self.embeddings = embeddings

        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        np.save(EMBEDDINGS_FILE, embeddings)

        with METADATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        return {
            "jobs": len(jobs),
            "chunks": len(self.chunks),
            "dimensions": int(embeddings.shape[1]),
        }

    def load_index(self) -> bool:
        """Load an existing local index. Returns False if none exists."""
        if not EMBEDDINGS_FILE.exists() or not METADATA_FILE.exists():
            return False

        self.embeddings = np.load(EMBEDDINGS_FILE)

        with METADATA_FILE.open("r", encoding="utf-8") as f:
            self.chunks = json.load(f)

        return True

    def ensure_index(self) -> None:
        """Load the existing index or build it if necessary."""
        if not self.load_index():
            self.build_index()

    def search(
        self,
        query: str,
        top_k: int = 5,
        section_filter: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most semantically relevant job chunks.

        Duplicate job postings are collapsed so the final result represents
        distinct internships rather than several chunks from the same job.
        """
        if not query or not query.strip():
            return []

        self.ensure_index()

        if self.embeddings is None or not self.chunks:
            return []

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)

        scores = self.embeddings @ query_embedding

        candidate_indices = np.argsort(scores)[::-1]

        results = []
        seen_jobs = set()

        for index in candidate_indices:
            chunk = self.chunks[int(index)]

            if section_filter and chunk["section"] != section_filter:
                continue

            job_id = chunk["job_id"]

            if job_id in seen_jobs:
                continue

            seen_jobs.add(job_id)

            results.append(
                {
                    "job_id": job_id,
                    "section": chunk["section"],
                    "chunk_text": chunk["text"],
                    "similarity": round(float(scores[int(index)]), 4),
                }
            )

            if len(results) >= top_k:
                break

        return results


_default_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Return a reusable application-level RAG pipeline instance."""
    global _default_pipeline

    if _default_pipeline is None:
        _default_pipeline = RAGPipeline()

    return _default_pipeline


def semantic_search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for application code."""
    return get_rag_pipeline().search(query, top_k=top_k)


if __name__ == "__main__":
    rag = RAGPipeline()

    print("Building internship RAG index...")
    stats = rag.build_index()
    print(
        f"Indexed {stats['jobs']} jobs, "
        f"{stats['chunks']} chunks, "
        f"{stats['dimensions']}-dimensional embeddings."
    )

    print("\nSample semantic search:")
    query = "Python backend internship with SQL, Flask and Docker"
    results = rag.search(query, top_k=5)

    for i, result in enumerate(results, start=1):
        print(
            f"{i}. {result['job_id']} | "
            f"{result['section']} | "
            f"similarity={result['similarity']}"
        )

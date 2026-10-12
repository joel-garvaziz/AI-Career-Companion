"""
Milestone 2.2 utility — Build the internship vector index.

Run from the project root:

    python build_rag_index.py

This reads the 180 postings from jobs_dataset.py, creates meaningful chunks,
generates Sentence Transformer embeddings, and saves the local index under
rag_index/.
"""

from rag_pipeline import RAGPipeline


def main():
    pipeline = RAGPipeline()
    stats = pipeline.build_index()

    print("\nRAG index created successfully.")
    print(f"Jobs indexed      : {stats['jobs']}")
    print(f"Chunks indexed    : {stats['chunks']}")
    print(f"Embedding size    : {stats['dimensions']}")
    print("Index directory   : rag_index/")


if __name__ == "__main__":
    main()

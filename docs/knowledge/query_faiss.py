import argparse
import json
from pathlib import Path

import faiss
import numpy as np

from build_faiss_index import FAISS_INDEX, METADATA_JSON, VECTORIZER_JSON, vectorize


def load_assets() -> tuple[faiss.Index, list[dict], dict[str, int], list[float]]:
    index = faiss.read_index(str(FAISS_INDEX))
    metadata = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
    vectorizer = json.loads(VECTORIZER_JSON.read_text(encoding="utf-8"))
    vocab = {key: int(value) for key, value in vectorizer["vocab"].items()}
    idf = [float(value) for value in vectorizer["idf"]]
    return index, metadata, vocab, idf


def infer_filters(query: str) -> dict:
    q = query.lower()
    inferred: dict[str, list[str]] = {}

    if any(term in q for term in ["label", "labels", "owner", "cost center", "cost-center"]):
        inferred["topics"] = ["labels"]
    elif any(term in q for term in ["dataset", "bigquery", "schema", "bq ", "terraform"]):
        inferred["topics"] = ["bigquery-datasets"]
    elif any(term in q for term in ["ops agent", "telemetry", "memory metric", "memory telemetry"]):
        inferred["topics"] = ["ops-agent"]
    elif any(term in q for term in ["machine type", "machine types", "rightsizing", "right sizing", "shared-core"]):
        inferred["topics"] = ["machine-types"]
    elif any(term in q for term in ["cpu utilization", "metric", "metrics catalog", "network bytes", "uptime metric"]):
        inferred["topics"] = ["gcp-compute-metrics"]

    usages: list[str] = []
    if any(term in q for term in ["memory telemetry", "missing telemetry", "missing observability", "ops agent"]):
        usages.extend(["missing-observability", "memory-metrics", "agent-installation"])
    if any(term in q for term in ["terraform", "dataset", "bigquery export"]):
        usages.extend(["dataset-setup", "bigquery-export"])
    if any(term in q for term in ["label", "owner", "cost center", "cost-center"]):
        usages.extend(["governance", "owner-labels", "cost-center-labels"])
    if any(term in q for term in ["rightsizing", "machine type", "machine types"]):
        usages.extend(["rightsizing", "machine-type-selection"])
    if any(term in q for term in ["cpu utilization", "metric", "cpu metric"]):
        usages.extend(["cpu-metrics", "snapshot-analysis"])

    if usages:
        inferred["usages"] = sorted(set(usages))

    return inferred


def filter_candidate_indices(
    metadata: list[dict],
    *,
    topics: list[str] | None = None,
    usages: list[str] | None = None,
    doc_ids: list[str] | None = None,
) -> list[int]:
    indices: list[int] = []
    for i, row in enumerate(metadata):
        if topics and row["topic"] not in topics:
            continue
        if doc_ids and row["doc_id"] not in doc_ids:
            continue
        if usages and not any(tag in usages for tag in row["usage"]):
            continue
        indices.append(i)
    return indices


def search(
    query: str,
    top_k: int,
    *,
    topics: list[str] | None = None,
    usages: list[str] | None = None,
    doc_ids: list[str] | None = None,
    auto_filter: bool = False,
) -> list[dict]:
    index, metadata, vocab, idf = load_assets()
    query_vec = vectorize(query, vocab, idf).astype(np.float32)
    if np.linalg.norm(query_vec) == 0:
        return []

    inferred = infer_filters(query) if auto_filter else {}
    effective_topics = topics or inferred.get("topics")
    effective_usages = usages or inferred.get("usages")
    effective_doc_ids = doc_ids

    candidate_indices = filter_candidate_indices(
        metadata,
        topics=effective_topics,
        usages=effective_usages,
        doc_ids=effective_doc_ids,
    )

    search_k = max(top_k * 5, 20)
    if candidate_indices:
        scores, indices = index.search(query_vec.reshape(1, -1), min(search_k, len(metadata)))
    else:
        scores, indices = index.search(query_vec.reshape(1, -1), top_k)

    results: list[dict] = []
    candidate_set = set(candidate_indices) if candidate_indices else None
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        if candidate_set is not None and idx not in candidate_set:
            continue
        row = metadata[idx].copy()
        row["score"] = round(float(score), 4)
        results.append(row)
        if len(results) >= top_k:
            break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the local FAISS knowledge index.")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--topic", action="append", dest="topics", help="Restrict retrieval to a topic; repeatable")
    parser.add_argument("--usage", action="append", dest="usages", help="Restrict retrieval to a usage tag; repeatable")
    parser.add_argument("--doc-id", action="append", dest="doc_ids", help="Restrict retrieval to a doc_id; repeatable")
    parser.add_argument("--auto-filter", action="store_true", help="Infer topic/usage filters from the query")
    args = parser.parse_args()

    results = search(
        args.query,
        args.top_k,
        topics=args.topics,
        usages=args.usages,
        doc_ids=args.doc_ids,
        auto_filter=args.auto_filter,
    )
    if not results:
        print("No results. Query terms may be outside the current local vocabulary.")
        return

    print(f"Query: {args.query}")
    print(f"Top {len(results)} results")
    if args.topics:
        print(f"Topic filter: {', '.join(args.topics)}")
    if args.usages:
        print(f"Usage filter: {', '.join(args.usages)}")
    if args.doc_ids:
        print(f"Doc filter: {', '.join(args.doc_ids)}")
    if args.auto_filter:
        inferred = infer_filters(args.query)
        if inferred:
            inferred_parts = []
            if inferred.get("topics"):
                inferred_parts.append(f"topics={','.join(inferred['topics'])}")
            if inferred.get("usages"):
                inferred_parts.append(f"usages={','.join(inferred['usages'])}")
            print(f"Auto filter: {'; '.join(inferred_parts)}")
    for rank, result in enumerate(results, 1):
        print()
        print(f"{rank}. {result['title']} [{result['doc_id']}] score={result['score']}")
        print(f"   source: {result['source']}")
        print(f"   usage: {', '.join(result['usage'])}")
        excerpt = result["content"].replace("\n", " ").strip()
        print(f"   excerpt: {excerpt[:260]}")


if __name__ == "__main__":
    main()

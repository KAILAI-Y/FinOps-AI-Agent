import argparse
import json
import os
from functools import lru_cache
from pathlib import Path
import sys

import faiss
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from query_faiss import filter_candidate_indices, infer_filters

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
torch.set_num_threads(1)


BASE_DIR = Path(__file__).resolve().parent
INDEX_DIR = BASE_DIR / "index"
SEMANTIC_FAISS_INDEX = INDEX_DIR / "knowledge_semantic.faiss"
SEMANTIC_METADATA_JSON = INDEX_DIR / "semantic_metadata.json"
SEMANTIC_CONFIG_JSON = INDEX_DIR / "semantic_index_config.json"


def mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    masked = last_hidden_state * mask
    summed = masked.sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-9)
    return summed / counts


@lru_cache(maxsize=1)
def load_assets() -> tuple[faiss.Index, list[dict], dict, AutoTokenizer, AutoModel]:
    index = faiss.read_index(str(SEMANTIC_FAISS_INDEX))
    metadata = json.loads(SEMANTIC_METADATA_JSON.read_text(encoding="utf-8"))
    config = json.loads(SEMANTIC_CONFIG_JSON.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    model = AutoModel.from_pretrained(config["model_name"])
    model.eval()
    return index, metadata, config, tokenizer, model


def encode_query(tokenizer: AutoTokenizer, model: AutoModel, query: str) -> np.ndarray:
    with torch.inference_mode():
        encoded = tokenizer([query], padding=True, truncation=True, return_tensors="pt")
        outputs = model(**encoded)
        pooled = mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
    return normalized.cpu().numpy().astype(np.float32)


def encode_queries(tokenizer: AutoTokenizer, model: AutoModel, queries: list[str]) -> np.ndarray:
    with torch.inference_mode():
        encoded = tokenizer(queries, padding=True, truncation=True, return_tensors="pt")
        outputs = model(**encoded)
        pooled = mean_pool(outputs.last_hidden_state, encoded["attention_mask"])
        normalized = torch.nn.functional.normalize(pooled, p=2, dim=1)
    return normalized.cpu().numpy().astype(np.float32)


def search(
    query: str,
    top_k: int,
    *,
    topics: list[str] | None = None,
    usages: list[str] | None = None,
    doc_ids: list[str] | None = None,
    auto_filter: bool = False,
) -> list[dict]:
    index, metadata, _, tokenizer, model = load_assets()
    query_vec = encode_query(tokenizer, model, query)
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
        scores, indices = index.search(query_vec, min(search_k, len(metadata)))
    else:
        scores, indices = index.search(query_vec, top_k)

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


def batch_search(items: list[dict], default_top_k: int = 5) -> list[dict]:
    index, metadata, _, tokenizer, model = load_assets()
    queries = [item["query"] for item in items]
    matrix = encode_queries(tokenizer, model, queries)
    payloads: list[dict] = []

    for item, query_vec in zip(items, matrix):
        top_k = int(item.get("top_k", default_top_k))
        query = item["query"]
        if np.linalg.norm(query_vec) == 0:
            payloads.append(
                {
                    "query": query,
                    "topics": item.get("topics"),
                    "usages": item.get("usages"),
                    "doc_ids": item.get("doc_ids"),
                    "auto_filter": bool(item.get("auto_filter", False)),
                    "results": [],
                }
            )
            continue

        inferred = infer_filters(query) if item.get("auto_filter", False) else {}
        effective_topics = item.get("topics") or inferred.get("topics")
        effective_usages = item.get("usages") or inferred.get("usages")
        effective_doc_ids = item.get("doc_ids")

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

        payloads.append(
            {
                "query": query,
                "topics": item.get("topics"),
                "usages": item.get("usages"),
                "doc_ids": item.get("doc_ids"),
                "auto_filter": bool(item.get("auto_filter", False)),
                "results": results,
            }
        )

    return payloads


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the local semantic FAISS knowledge index.")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--topic", action="append", dest="topics", help="Restrict retrieval to a topic; repeatable")
    parser.add_argument("--usage", action="append", dest="usages", help="Restrict retrieval to a usage tag; repeatable")
    parser.add_argument("--doc-id", action="append", dest="doc_ids", help="Restrict retrieval to a doc_id; repeatable")
    parser.add_argument("--auto-filter", action="store_true", help="Infer topic/usage filters from the query")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Emit machine-readable JSON results")
    parser.add_argument("--batch-json", action="store_true", help="Read a batch JSON payload from stdin")
    args = parser.parse_args()

    if args.batch_json:
        payload = json.loads(sys.stdin.read())
        items = payload.get("queries", [])
        results = batch_search(items, default_top_k=payload.get("top_k", 5))
        print(json.dumps({"queries": results}, ensure_ascii=False))
        return

    if not args.query:
        parser.error("query is required unless --batch-json is used")

    results = search(
        args.query,
        args.top_k,
        topics=args.topics,
        usages=args.usages,
        doc_ids=args.doc_ids,
        auto_filter=args.auto_filter,
    )
    if not results:
        if args.json_output:
            print(json.dumps({"query": args.query, "results": []}, ensure_ascii=False))
        else:
            print("No results.")
        return

    if args.json_output:
        payload = {
            "query": args.query,
            "topics": args.topics,
            "usages": args.usages,
            "doc_ids": args.doc_ids,
            "auto_filter": args.auto_filter,
            "results": results,
        }
        print(json.dumps(payload, ensure_ascii=False))
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

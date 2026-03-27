import json
from pathlib import Path

from query_faiss import search


BASE_DIR = Path(__file__).resolve().parent
EVAL_DIR = BASE_DIR / "eval"
EVAL_JSON = EVAL_DIR / "retrieval_eval.json"
EVAL_MD = EVAL_DIR / "retrieval_eval.md"

TOP_K = 5
HIT_LEVELS = (1, 3, 5)

EVAL_CASES = [
    {
        "id": "labels_add",
        "query": "how to add labels to compute engine resources",
        "expected_topics": ["labels"],
        "expected_docs": ["compute-labels"],
        "expected_usage": ["governance", "owner-labels"],
    },
    {
        "id": "labels_filter",
        "query": "how to filter compute engine resources by labels",
        "expected_topics": ["labels"],
        "expected_docs": ["compute-labels"],
        "expected_usage": ["governance"],
    },
    {
        "id": "dataset_terraform",
        "query": "how to create a dataset with terraform",
        "expected_topics": ["bigquery-datasets"],
        "expected_docs": ["bigquery-datasets"],
        "expected_usage": ["dataset-setup", "bigquery-export"],
    },
    {
        "id": "dataset_sql",
        "query": "how to create a dataset with sql in bigquery",
        "expected_topics": ["bigquery-datasets"],
        "expected_docs": ["bigquery-datasets"],
        "expected_usage": ["dataset-setup"],
    },
    {
        "id": "ops_install_linux",
        "query": "how to install the ops agent on linux",
        "expected_topics": ["ops-agent"],
        "expected_docs": ["ops-agent-installation"],
        "expected_usage": ["agent-installation", "missing-observability"],
    },
    {
        "id": "ops_install_windows",
        "query": "how to install the ops agent on windows",
        "expected_topics": ["ops-agent"],
        "expected_docs": ["ops-agent-installation"],
        "expected_usage": ["agent-installation", "missing-observability"],
    },
    {
        "id": "memory_telemetry",
        "query": "why is memory telemetry missing on a vm",
        "expected_topics": ["ops-agent"],
        "expected_docs": ["ops-agent-installation", "ops-agent-overview"],
        "expected_usage": ["missing-observability", "memory-metrics"],
    },
    {
        "id": "cpu_metric",
        "query": "what metric shows compute engine cpu utilization",
        "expected_topics": ["gcp-compute-metrics"],
        "expected_docs": ["gcp-metrics-catalog"],
        "expected_usage": ["cpu-metrics", "snapshot-analysis"],
    },
    {
        "id": "machine_types",
        "query": "how to compare compute engine machine types for rightsizing",
        "expected_topics": ["machine-types"],
        "expected_docs": ["compute-machine-types"],
        "expected_usage": ["rightsizing", "machine-type-selection"],
    },
    {
        "id": "labels_cost_center",
        "query": "why should i use owner and cost center labels",
        "expected_topics": ["labels"],
        "expected_docs": ["compute-labels"],
        "expected_usage": ["owner-labels", "cost-center-labels"],
    },
]


def score_case(results: list[dict], case: dict) -> dict:
    topic_hit = any(row["topic"] in case["expected_topics"] for row in results)
    doc_hit = any(row["doc_id"] in case["expected_docs"] for row in results)
    usage_hit = any(any(tag in case["expected_usage"] for tag in row["usage"]) for row in results)
    pass_case = topic_hit and doc_hit and usage_hit

    hit_rates = {}
    for k in HIT_LEVELS:
        subset = results[:k]
        hit_rates[f"top_{k}"] = {
            "topic_hit": any(row["topic"] in case["expected_topics"] for row in subset),
            "doc_hit": any(row["doc_id"] in case["expected_docs"] for row in subset),
            "usage_hit": any(any(tag in case["expected_usage"] for tag in row["usage"]) for row in subset),
        }

    return {
        "topic_hit": topic_hit,
        "doc_hit": doc_hit,
        "usage_hit": usage_hit,
        "pass": pass_case,
        "hit_rates": hit_rates,
    }


def summarize_results(evaluated_cases: list[dict]) -> dict:
    total = len(evaluated_cases)
    passed = sum(1 for case in evaluated_cases if case["checks"]["pass"])
    topic_hits = sum(1 for case in evaluated_cases if case["checks"]["topic_hit"])
    doc_hits = sum(1 for case in evaluated_cases if case["checks"]["doc_hit"])
    usage_hits = sum(1 for case in evaluated_cases if case["checks"]["usage_hit"])
    hit_summary = {}
    for k in HIT_LEVELS:
        key = f"top_{k}"
        hit_summary[key] = {
            "topic_hit_rate": round(
                sum(1 for case in evaluated_cases if case["checks"]["hit_rates"][key]["topic_hit"]) / total, 4
            )
            if total
            else 0.0,
            "doc_hit_rate": round(
                sum(1 for case in evaluated_cases if case["checks"]["hit_rates"][key]["doc_hit"]) / total, 4
            )
            if total
            else 0.0,
            "usage_hit_rate": round(
                sum(1 for case in evaluated_cases if case["checks"]["hit_rates"][key]["usage_hit"]) / total, 4
            )
            if total
            else 0.0,
        }
    return {
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "topic_hit_rate": round(topic_hits / total, 4) if total else 0.0,
        "doc_hit_rate": round(doc_hits / total, 4) if total else 0.0,
        "usage_hit_rate": round(usage_hits / total, 4) if total else 0.0,
        "top_k": TOP_K,
        "hit_rates": hit_summary,
    }


def render_markdown(summary: dict, evaluated_cases: list[dict]) -> str:
    lines = [
        "# Retrieval Eval Report",
        "",
        f"- Total cases: {summary['total_cases']}",
        f"- Passed: {summary['passed_cases']}",
        f"- Pass rate: {summary['pass_rate']}",
        f"- Topic hit rate: {summary['topic_hit_rate']}",
        f"- Doc hit rate: {summary['doc_hit_rate']}",
        f"- Usage hit rate: {summary['usage_hit_rate']}",
        f"- Top-k: {summary['top_k']}",
        "",
        "## Rank Metrics",
        "",
    ]

    for k in HIT_LEVELS:
        row = summary["hit_rates"][f"top_{k}"]
        lines.extend(
            [
                f"- Top-{k} topic hit rate: {row['topic_hit_rate']}",
                f"- Top-{k} doc hit rate: {row['doc_hit_rate']}",
                f"- Top-{k} usage hit rate: {row['usage_hit_rate']}",
            ]
        )

    lines.extend(
        [
            "",
        "## Cases",
        "",
        ]
    )

    for case in evaluated_cases:
        checks = case["checks"]
        status = "PASS" if checks["pass"] else "FAIL"
        lines.append(f"### {case['id']} - {status}")
        lines.append("")
        lines.append(f"- Query: `{case['query']}`")
        lines.append(f"- Topic hit: `{checks['topic_hit']}`")
        lines.append(f"- Doc hit: `{checks['doc_hit']}`")
        lines.append(f"- Usage hit: `{checks['usage_hit']}`")
        for k in HIT_LEVELS:
            row = checks["hit_rates"][f"top_{k}"]
            lines.append(
                f"- Top-{k}: topic=`{row['topic_hit']}` doc=`{row['doc_hit']}` usage=`{row['usage_hit']}`"
            )
        lines.append("- Top results:")
        for row in case["results"][:3]:
            lines.append(
                f"  - `{row['title']}` | topic=`{row['topic']}` | doc=`{row['doc_id']}` | score=`{row['score']}`"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    evaluated_cases = []
    for case in EVAL_CASES:
        results = search(case["query"], TOP_K)
        checks = score_case(results, case)
        evaluated_cases.append(
            {
                "id": case["id"],
                "query": case["query"],
                "expected_topics": case["expected_topics"],
                "expected_docs": case["expected_docs"],
                "expected_usage": case["expected_usage"],
                "checks": checks,
                "results": results,
            }
        )

    summary = summarize_results(evaluated_cases)
    payload = {
        "summary": summary,
        "cases": evaluated_cases,
    }

    EVAL_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EVAL_MD.write_text(render_markdown(summary, evaluated_cases), encoding="utf-8")

    print(f"evaluated {summary['total_cases']} cases")
    print(f"passed {summary['passed_cases']} cases")
    print(f"pass rate {summary['pass_rate']}")
    print(EVAL_JSON)
    print(EVAL_MD)


if __name__ == "__main__":
    main()

import json
from pathlib import Path

from eval_retrieval import EVAL_CASES, HIT_LEVELS, TOP_K, render_markdown, score_case, summarize_results
from query_semantic import search


BASE_DIR = Path(__file__).resolve().parent
EVAL_DIR = BASE_DIR / "eval"
EVAL_JSON = EVAL_DIR / "retrieval_eval_semantic.json"
EVAL_MD = EVAL_DIR / "retrieval_eval_semantic.md"


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    evaluated_cases = []
    for case in EVAL_CASES:
        results = search(case["query"], TOP_K, auto_filter=True)
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
    for k in HIT_LEVELS:
        row = summary["hit_rates"][f"top_{k}"]
        print(
            f"top-{k} topic/doc/usage = "
            f"{row['topic_hit_rate']}/{row['doc_hit_rate']}/{row['usage_hit_rate']}"
        )
    print(EVAL_JSON)
    print(EVAL_MD)


if __name__ == "__main__":
    main()

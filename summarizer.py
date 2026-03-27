import json
import os
import subprocess
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
METRICS_PATH = OUTPUTS_DIR / "metrics.json"
RECOMMENDATIONS_PATH = OUTPUTS_DIR / "recommendations.json"
REPORT_JSON_PATH = OUTPUTS_DIR / "finops_report.json"
REPORT_MD_PATH = OUTPUTS_DIR / "finops_report.md"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
TREND_CATEGORIES = {"persistent-low-utilization", "idle-but-expensive"}
GROUNDING_QUERY_MAP = {
    "missing-observability": {
        "query": "why is memory telemetry missing on a vm",
        "reason": "Explain missing memory telemetry and Ops Agent requirements.",
    },
    "governance": {
        "query": "why should i use owner and cost center labels",
        "reason": "Explain governance and chargeback value of labels.",
    },
    "review-before-rightsizing": {
        "query": "how to compare compute engine machine types for rightsizing",
        "reason": "Support cautious rightsizing guidance with machine type context.",
    },
    "persistent-low-utilization": {
        "query": "how to compare compute engine machine types for rightsizing",
        "reason": "Support trend-based rightsizing candidates with machine type context.",
    },
    "idle-but-expensive": {
        "query": "how to compare compute engine machine types for rightsizing",
        "reason": "Support cost-focused rightsizing review with machine type context.",
    },
    "high-cpu-sustained": {
        "query": "what metric shows compute engine cpu utilization",
        "reason": "Ground sustained CPU review in official metric definitions.",
    },
    "high-network-throughput": {
        "query": "what metric shows compute engine cpu utilization",
        "reason": "Ground throughput review in metric catalog context.",
    },
    "high-disk-activity": {
        "query": "what metric shows compute engine cpu utilization",
        "reason": "Ground disk activity review in metric catalog context.",
    },
    "lifecycle": {
        "query": "what costs can remain after a compute engine vm is terminated",
        "reason": "Explain separately billed resources such as disks and static external IPs after VM termination.",
    },
}


def load_env_from_file(filename=".env"):
    env_path = BASE_DIR / filename
    if not env_path.is_file():
        return None

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    return env_path


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def build_grounding_queries(recommendations):
    seen_queries = set()
    grounding_queries = []
    for recommendation in recommendations:
        category = recommendation.get("category")
        entry = GROUNDING_QUERY_MAP.get(category)
        if not entry:
            continue
        if entry["query"] in seen_queries:
            continue
        seen_queries.add(entry["query"])
        grounding_queries.append(
            {
                "category": category,
                "query": entry["query"],
                "reason": entry["reason"],
            }
        )
    return grounding_queries


def build_grounding_context(recommendations, top_k_per_query=2, max_evidence=6):
    queries = build_grounding_queries(recommendations)
    if not queries:
        return {
            "mode": "none",
            "status": "no-matching-findings",
            "queries": [],
            "evidence": [],
        }

    evidence = []
    seen_ids = set()
    semantic_query_script = BASE_DIR / "docs" / "knowledge" / "query_semantic.py"
    if not semantic_query_script.is_file():
        return {
            "mode": "none",
            "status": "unavailable",
            "error": "query_semantic.py not found",
            "queries": queries,
            "evidence": [],
        }

    try:
        completed = subprocess.run(
            [
                "python3",
                str(semantic_query_script),
                "--batch-json",
            ],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=90,
            input=json.dumps(
                {
                    "top_k": top_k_per_query,
                    "queries": [
                        {
                            "query": query_item["query"],
                            "auto_filter": True,
                        }
                        for query_item in queries
                    ],
                }
            ),
        )
        payload = json.loads(completed.stdout)
        batched_results = payload.get("queries", [])
    except Exception as exc:
        return {
            "mode": "none",
            "status": "query-failed",
            "error": str(exc),
            "queries": queries,
            "evidence": evidence,
        }

    for query_item, result_payload in zip(queries, batched_results):
        results = result_payload.get("results", [])
        for row in results:
            evidence_id = row["id"]
            if evidence_id in seen_ids:
                continue
            seen_ids.add(evidence_id)
            evidence.append(
                {
                    "id": row["id"],
                    "category": query_item["category"],
                    "query": query_item["query"],
                    "reason": query_item["reason"],
                    "title": row["title"],
                    "topic": row["topic"],
                    "doc_id": row["doc_id"],
                    "source": row["source"],
                    "usage": row["usage"],
                    "score": row["score"],
                    "content": row["content"],
                }
            )
            if len(evidence) >= max_evidence:
                break
        if len(evidence) >= max_evidence:
            break

    return {
        "mode": "semantic-faiss",
        "status": "ok",
        "queries": queries,
        "evidence": evidence,
    }


def build_grounding_references(context):
    grounding = context.get("grounding") or {}
    evidence = grounding.get("evidence") or []
    recommendations = context.get("recommendations") or []
    if not evidence:
        return {
            "why_it_matters_evidence": [],
            "recommended_action_evidence": [],
            "decision_rule_evidence": [],
        }

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    prioritized = sorted(
        recommendations,
        key=lambda recommendation: (
            severity_rank.get(recommendation.get("severity", "low"), 3),
            recommendation.get("category", ""),
        ),
    )
    primary_category = prioritized[0].get("category") if prioritized else None

    def select_ids(categories):
        if not categories:
            return [item["id"] for item in evidence[:2]]
        matched = [item["id"] for item in evidence if item.get("category") in categories]
        return matched[:2] if matched else [item["id"] for item in evidence[:2]]

    action_categories = [primary_category] if primary_category else []
    if primary_category in {"review-before-rightsizing", "persistent-low-utilization", "idle-but-expensive"}:
        action_categories = list(
            {
                primary_category,
                "review-before-rightsizing",
                "persistent-low-utilization",
                "idle-but-expensive",
            }
        )

    return {
        "why_it_matters_evidence": select_ids([primary_category] if primary_category else []),
        "recommended_action_evidence": select_ids(action_categories),
        "decision_rule_evidence": select_ids(action_categories),
    }


def build_footnote_index(evidence):
    footnote_map = {}
    ordered = []
    for item in evidence:
        evidence_id = item.get("id")
        if evidence_id and evidence_id not in footnote_map:
            footnote_map[evidence_id] = len(ordered) + 1
            ordered.append(item)
    return footnote_map, ordered


def format_footnote_refs(evidence_ids, footnote_map):
    refs = [f"[^{footnote_map[evidence_id]}]" for evidence_id in evidence_ids if evidence_id in footnote_map]
    return "".join(refs)


def build_report_context(metrics, recommendations):
    total_instances = len(metrics)
    running_instances = sum(1 for metric in metrics if metric.get("status") == "RUNNING")
    total_estimated_monthly_cost = round(
        sum(metric.get("estimated_monthly_cost") or 0 for metric in metrics), 2
    )
    recommendation_counts = {}
    for recommendation in recommendations:
        category = recommendation["category"]
        recommendation_counts[category] = recommendation_counts.get(category, 0) + 1
    trend_summary = build_trend_summary(metrics)
    finding_breakdown = build_finding_breakdown(recommendations)
    domain_counts = build_domain_counts(recommendations)

    return {
        "total_instances": total_instances,
        "running_instances": running_instances,
        "total_estimated_monthly_cost": total_estimated_monthly_cost,
        "recommendation_counts": recommendation_counts,
        "domain_counts": domain_counts,
        "trend_summary": trend_summary,
        "finding_breakdown": finding_breakdown,
        "metrics": metrics,
        "recommendations": recommendations,
    }


def build_trend_summary(metrics):
    trend_ready_instances = sum(
        1 for metric in metrics if metric.get("seven_day_avg_cpu") is not None
    )
    idle_but_expensive_instances = [
        metric["instance_name"]
        for metric in metrics
        if metric.get("idle_but_expensive_flag")
    ]
    persistent_low_utilization_instances = [
        metric["instance_name"]
        for metric in metrics
        if (metric.get("seven_day_low_utilization_days") or 0) >= 3
    ]
    return {
        "trend_ready_instances": trend_ready_instances,
        "idle_but_expensive_instances": idle_but_expensive_instances,
        "persistent_low_utilization_instances": persistent_low_utilization_instances,
    }


def build_finding_breakdown(recommendations):
    snapshot_findings = []
    trend_findings = []
    for recommendation in recommendations:
        target = trend_findings if recommendation.get("category") in TREND_CATEGORIES else snapshot_findings
        target.append(
            {
                "instance_name": recommendation.get("instance_name", "unknown"),
                "domain": recommendation.get("domain", "unknown"),
                "category": recommendation.get("category", "unknown"),
                "severity": recommendation.get("severity", "unknown"),
                "action_priority": recommendation.get("action_priority", "unknown"),
                "needs_human_review": recommendation.get("needs_human_review", True),
                "recommended_owner": recommendation.get("recommended_owner", "unknown"),
                "summary": recommendation.get("summary", ""),
            }
        )
    return {
        "snapshot_findings": snapshot_findings,
        "trend_findings": trend_findings,
    }


def build_domain_counts(recommendations):
    domain_counts = {}
    for recommendation in recommendations:
        domain = recommendation.get("domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    return domain_counts


def build_fallback_summary(context):
    recommendations = context["recommendations"]
    metrics = context["metrics"]
    running_instances = context["running_instances"]
    total_instances = context["total_instances"]
    total_cost = context["total_estimated_monthly_cost"]
    trend_summary = context.get("trend_summary", {})
    finding_breakdown = context.get("finding_breakdown", {})
    domain_counts = context.get("domain_counts", {})
    snapshot_findings = finding_breakdown.get("snapshot_findings", [])
    trend_findings = finding_breakdown.get("trend_findings", [])

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    prioritized_recommendations = sorted(
        recommendations,
        key=lambda recommendation: (
            severity_rank.get(recommendation.get("severity", "low"), 3),
            recommendation.get("category", ""),
        ),
    )

    current_state = (
        f"Observed {total_instances} VM(s), with {running_instances} currently running."
    )
    if running_instances < total_instances:
        current_state += (
            " Some recommendations may reflect recent activity inside the lookback window even if a VM is now stopped."
        )

    lines = [
        current_state,
        f"Estimated monthly run cost across sampled VMs: ${total_cost}.",
    ]
    if trend_summary.get("trend_ready_instances"):
        lines.append(
            f"Historical trend coverage is available for {trend_summary['trend_ready_instances']} VM(s) over the last 7 days."
        )
    if trend_summary.get("persistent_low_utilization_instances"):
        lines.append(
            "Persistent low-utilization candidates: "
            + ", ".join(trend_summary["persistent_low_utilization_instances"][:3])
            + "."
        )
    lines.append(
        f"Snapshot findings: {len(snapshot_findings)}. Trend findings: {len(trend_findings)}."
    )
    if domain_counts:
        domain_parts = [f"{domain} {count}" for domain, count in sorted(domain_counts.items())]
        lines.append("Domain breakdown: " + ", ".join(domain_parts) + ".")

    headline = "No material optimization findings in current sample."
    if prioritized_recommendations:
        top_recommendation = prioritized_recommendations[0]
        headline = (
            f"Top finding: {top_recommendation['instance_name']} requires "
            f"{top_recommendation['category']} review."
        )
        lines.append(
            f"Highest-priority finding is {top_recommendation['category']} "
            f"with {top_recommendation['severity']} severity."
        )
    else:
        lines.append("No optimization findings were generated for the current sample.")

    actions = []
    seen_actions = set()
    for recommendation in prioritized_recommendations:
        action = recommendation["suggested_action"]
        if action not in seen_actions:
            actions.append(action)
            seen_actions.add(action)
        if len(actions) == 3:
            break

    risks = []
    categories = {recommendation["category"] for recommendation in prioritized_recommendations}
    if "review-before-rightsizing" in categories:
        risks.append("Low CPU alone is not enough to justify downsizing because the workload still shows meaningful disk or network activity.")
    if "lifecycle" in categories:
        risks.append("Stopped instances can still incur cost through attached disks, reserved IPs, or other leftover resources.")
    if "governance" in categories:
        risks.append("Missing ownership labels make chargeback and remediation routing slower.")
    if trend_summary.get("idle_but_expensive_instances"):
        risks.append(
            "Some VMs appear both persistently underutilized and relatively expensive, which makes them stronger optimization candidates."
        )
    if not risks and prioritized_recommendations:
        risks.append("Optimization findings should be validated against workload criticality before action is taken.")

    top_recommendation = prioritized_recommendations[0] if prioritized_recommendations else None

    return {
        "headline": headline,
        "summary": " ".join(lines),
        "primary_candidate": top_recommendation["instance_name"] if top_recommendation else "None",
        "why_it_matters": (
            top_recommendation["rationale"]
            if top_recommendation
            else "No optimization findings were generated."
        ),
        "how_to_check": [
            "Open GCP Monitoring and inspect CPU, disk, and network charts for the last 24 hours.",
            "Check whether the VM supports batch transfer, logging, or other throughput-heavy jobs before changing machine size.",
            "Verify the instance labels and identify the owning team before taking any cost action.",
        ],
        "recommended_action": actions[0] if actions else "No action suggested.",
        "decision_rule": (
            "If CPU remains low and throughput spikes are infrequent, prefer scheduled runtime or cautious rightsizing; otherwise keep the current size."
            if top_recommendation
            else "No decision rule available."
        ),
        "actions": actions,
        "risks": risks,
        "mode": "deterministic",
        "snapshot_findings": snapshot_findings,
        "trend_findings": trend_findings,
    }


def build_gemini_prompt(context):
    return f"""
You are a FinOps analyst writing an actionable cloud cost optimization report.

Return JSON with exactly these keys:
- headline
- summary
- primary_candidate
- why_it_matters
- how_to_check
- recommended_action
- decision_rule
- actions
- risks

Requirements:
- summary: 2-4 sentences
- primary_candidate: the main VM or resource to review first
- why_it_matters: 1-2 concrete sentences citing the observed issue
- how_to_check: array of 2-4 specific checks using GCP Console, Monitoring, labels, or workload review
- recommended_action: one specific next action
- decision_rule: one sentence explaining when to proceed vs stop
- actions: array of 2-4 concise strings
- risks: array of 1-3 concise strings
- focus on cloud cost optimization, utilization, and governance
- use the provided grounding evidence when explaining platform-specific behavior such as missing telemetry, labels, metrics, or machine-type guidance
- if grounding evidence is present, prefer those snippets over generic cloud knowledge
- do not invent data not present in the input
- do not add any system state, billing fact, resource dependency, or operational event unless it is explicitly present in the input
- if a fact is not explicitly present in the input, do not imply it is true
- if you make a cautious inference, label it clearly as an inference or a possibility to verify
- never present assumptions as confirmed facts
- avoid vague statements like "review the resource" without saying what to inspect
- `estimated_monthly_cost` is only a reference cost for the VM when running, not proof of current spend after termination
- if the VM is TERMINATED, do not say it is definitely still incurring the full VM run cost
- for disks, static IPs, or other leftover charges, present them as possibilities to verify, not confirmed facts unless explicitly present in the input
- distinguish clearly between observed facts, rule-based findings, and your own cautious inference
- do not cite any external document or recommendation that is not included in the input grounding evidence

Input:
{json.dumps(context, indent=2)}
""".strip()


def extract_gemini_text(payload):
    candidates = payload.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                return text
    return ""


def generate_gemini_summary(context):
    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key or not model:
        return None

    response = requests.post(
        f"{GEMINI_API_BASE_URL}/{model}:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "contents": [{"parts": [{"text": build_gemini_prompt(context)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "summary": {"type": "string"},
                        "primary_candidate": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "how_to_check": {"type": "array", "items": {"type": "string"}},
                        "recommended_action": {"type": "string"},
                        "decision_rule": {"type": "string"},
                        "actions": {"type": "array", "items": {"type": "string"}},
                        "risks": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "headline",
                        "summary",
                        "primary_candidate",
                        "why_it_matters",
                        "how_to_check",
                        "recommended_action",
                        "decision_rule",
                        "actions",
                        "risks",
                    ],
                },
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    content = extract_gemini_text(response.json())
    parsed = json.loads(content)
    parsed["mode"] = f"gemini:{model}"
    return parsed


def build_markdown_report(report):
    how_to_check = report.get("how_to_check") or []
    actions = report.get("actions") or []
    risks = report.get("risks") or []
    snapshot_findings = report.get("snapshot_findings") or []
    trend_findings = report.get("trend_findings") or []
    grounding = report.get("grounding") or {}
    evidence = grounding.get("evidence") or []
    why_it_matters_evidence = report.get("why_it_matters_evidence") or []
    recommended_action_evidence = report.get("recommended_action_evidence") or []
    decision_rule_evidence = report.get("decision_rule_evidence") or []
    footnote_map, ordered_evidence = build_footnote_index(evidence)

    lines = [
        "# FinOps Report",
        "",
        f"Mode: `{report['mode']}`",
        "",
        f"## {report['headline']}",
        "",
        report["summary"],
        "",
        "## Primary Candidate",
        report.get("primary_candidate", "None"),
        "",
        "## Why It Matters",
        report.get("why_it_matters", "No explanation available.") + format_footnote_refs(why_it_matters_evidence, footnote_map),
    ]
    lines.extend(
        [
        "",
        "## How To Check",
        ]
    )
    if how_to_check:
        lines.extend(f"- {item}" for item in how_to_check)
    else:
        lines.append("- No verification steps provided.")

    lines.extend(
        [
            "",
            "## Recommended Action",
            report.get("recommended_action", "No action suggested.") + format_footnote_refs(recommended_action_evidence, footnote_map),
        ]
    )
    lines.extend(
        [
            "",
            "## Decision Rule",
            report.get("decision_rule", "No decision rule available.") + format_footnote_refs(decision_rule_evidence, footnote_map),
        ]
    )
    lines.extend(
        [
            "",
            "## Additional Actions",
        ]
    )
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- No actions suggested.")

    lines.extend(
        [
            "",
            "## Snapshot Findings",
        ]
    )
    if snapshot_findings:
        lines.extend(
            f"- [{finding['severity']}] [{finding['domain']}] [{finding['action_priority']}] {finding['instance_name']} / {finding['category']}: {finding['summary']} | owner: {finding['recommended_owner']} | human-review: {finding['needs_human_review']}"
            for finding in snapshot_findings
        )
    else:
        lines.append("- No snapshot findings identified.")

    lines.extend(
        [
            "",
            "## Trend Findings",
        ]
    )
    if trend_findings:
        lines.extend(
            f"- [{finding['severity']}] [{finding['domain']}] [{finding['action_priority']}] {finding['instance_name']} / {finding['category']}: {finding['summary']} | owner: {finding['recommended_owner']} | human-review: {finding['needs_human_review']}"
            for finding in trend_findings
        )
    else:
        lines.append("- No trend findings identified.")

    lines.append("")
    lines.append("## Risks")
    if risks:
        lines.extend(f"- {risk}" for risk in risks)
    else:
        lines.append("- No material risks identified.")

    lines.append("")
    lines.append("## Grounding Evidence")
    if evidence:
        for item in evidence:
            lines.append(
                f"- [{item['topic']}] {item['title']} | source: {item['source']} | score: {item['score']}"
            )
    else:
        lines.append("- No retrieval grounding evidence attached to this run.")

    if ordered_evidence:
        lines.append("")
        lines.append("## Source Footnotes")
        for item in ordered_evidence:
            number = footnote_map[item["id"]]
            lines.append(
                f"[^{number}]: {item['title']} [{item['topic']}] | {item['source']} | score: {item['score']}"
            )

    return "\n".join(lines) + "\n"


def write_outputs(report):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as file_obj:
        json.dump(report, file_obj, indent=4)

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write(build_markdown_report(report))


def main():
    load_env_from_file()
    metrics = load_json(METRICS_PATH)
    recommendations = load_json(RECOMMENDATIONS_PATH)
    context = build_report_context(metrics, recommendations)
    context["grounding"] = build_grounding_context(recommendations)

    report = None
    try:
        report = generate_gemini_summary(context)
    except requests.RequestException as exc:
        print(f"Gemini summary failed, using deterministic fallback: {exc}")
    except json.JSONDecodeError as exc:
        print(f"Gemini returned non-JSON output, using deterministic fallback: {exc}")

    if report is None:
        report = build_fallback_summary(context)
    else:
        report["snapshot_findings"] = context["finding_breakdown"]["snapshot_findings"]
        report["trend_findings"] = context["finding_breakdown"]["trend_findings"]

    report["grounding"] = context.get("grounding", {})
    report.update(build_grounding_references(context))

    write_outputs(report)
    print(f"Report written: {REPORT_JSON_PATH.name}, {REPORT_MD_PATH.name} [{report['mode']}]")


if __name__ == "__main__":
    main()

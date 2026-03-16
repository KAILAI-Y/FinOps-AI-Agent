import json
import os
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
METRICS_PATH = OUTPUTS_DIR / "metrics.json"
RECOMMENDATIONS_PATH = OUTPUTS_DIR / "recommendations.json"
REPORT_JSON_PATH = OUTPUTS_DIR / "finops_report.json"
REPORT_MD_PATH = OUTPUTS_DIR / "finops_report.md"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


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

    return {
        "total_instances": total_instances,
        "running_instances": running_instances,
        "total_estimated_monthly_cost": total_estimated_monthly_cost,
        "recommendation_counts": recommendation_counts,
        "metrics": metrics,
        "recommendations": recommendations,
    }


def build_fallback_summary(context):
    recommendations = context["recommendations"]
    metrics = context["metrics"]
    running_instances = context["running_instances"]
    total_instances = context["total_instances"]
    total_cost = context["total_estimated_monthly_cost"]

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
- do not invent data not present in the input
- avoid vague statements like "review the resource" without saying what to inspect
- `estimated_monthly_cost` is only a reference cost for the VM when running, not proof of current spend after termination
- if the VM is TERMINATED, do not say it is definitely still incurring the full VM run cost
- for disks, static IPs, or other leftover charges, present them as possibilities to verify, not confirmed facts unless explicitly present in the input
- distinguish clearly between observed facts, rule-based findings, and your own cautious inference

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
        report.get("why_it_matters", "No explanation available."),
        "",
        "## How To Check",
    ]
    if how_to_check:
        lines.extend(f"- {item}" for item in how_to_check)
    else:
        lines.append("- No verification steps provided.")

    lines.extend(
        [
            "",
            "## Recommended Action",
            report.get("recommended_action", "No action suggested."),
            "",
            "## Decision Rule",
            report.get("decision_rule", "No decision rule available."),
            "",
            "## Additional Actions",
        ]
    )
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- No actions suggested.")

    lines.append("")
    lines.append("## Risks")
    if risks:
        lines.extend(f"- {risk}" for risk in risks)
    else:
        lines.append("- No material risks identified.")

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

    report = None
    try:
        report = generate_gemini_summary(context)
    except requests.RequestException as exc:
        print(f"Gemini summary failed, using deterministic fallback: {exc}")
    except json.JSONDecodeError as exc:
        print(f"Gemini returned non-JSON output, using deterministic fallback: {exc}")

    if report is None:
        report = build_fallback_summary(context)

    write_outputs(report)
    print(f"Report written: {REPORT_JSON_PATH.name}, {REPORT_MD_PATH.name} [{report['mode']}]")


if __name__ == "__main__":
    main()

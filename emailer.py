import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests

from summarizer import extract_gemini_text, load_env_from_file, load_json


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORT_JSON_PATH = OUTPUTS_DIR / "finops_report.json"
QUALITY_JSON_PATH = OUTPUTS_DIR / "quality_report.json"
TREND_JSON_PATH = OUTPUTS_DIR / "trend_analysis.json"
RECOMMENDATIONS_JSON_PATH = OUTPUTS_DIR / "recommendations.json"
EMAIL_JSON_PATH = OUTPUTS_DIR / "email_preview.json"
EMAIL_TXT_PATH = OUTPUTS_DIR / "email_preview.txt"
EMAIL_HTML_PATH = OUTPUTS_DIR / "email_preview.html"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
SRE_CATEGORIES = {
    "review-before-rightsizing",
    "memory-bound",
    "high-cpu-sustained",
    "high-memory-pressure",
    "missing-observability",
    "high-network-throughput",
    "high-disk-activity",
    "long-lived-running-instance",
}
GOVERNANCE_CATEGORIES = {"governance"}


def normalize_recommendation(finding):
    domain = finding.get("domain")
    if not domain:
        category = finding.get("category", "")
        if category in SRE_CATEGORIES:
            domain = "sre"
        elif category in GOVERNANCE_CATEGORIES:
            domain = "governance"
        else:
            domain = "finops"

    severity = finding.get("severity", "unknown")
    action_priority = finding.get("action_priority")
    if not action_priority:
        if severity == "high":
            action_priority = "p1"
        elif domain == "sre" and severity == "medium":
            action_priority = "p2"
        elif severity == "medium":
            action_priority = "p3"
        else:
            action_priority = "p4"

    needs_human_review = finding.get("needs_human_review")
    if needs_human_review is None:
        needs_human_review = severity != "low" or domain == "sre"

    return {
        "instance_name": finding.get("instance_name", "unknown"),
        "domain": domain,
        "category": finding.get("category", "unknown"),
        "severity": severity,
        "action_priority": action_priority,
        "needs_human_review": needs_human_review,
        "recommended_owner": finding.get("recommended_owner", "unknown"),
        "summary": finding.get("summary", ""),
    }


def build_email_context(report, quality_report, trend_analysis, recommendations):
    summary = trend_analysis.get("summary", {})
    snapshot_findings = [normalize_recommendation(item) for item in report.get("snapshot_findings", [])]
    trend_findings = [normalize_recommendation(item) for item in report.get("trend_findings", [])]
    normalized_recommendations = [normalize_recommendation(item) for item in recommendations]
    all_findings = snapshot_findings + trend_findings
    if not all_findings:
        all_findings = normalized_recommendations
    top_findings = sorted(
        all_findings,
        key=lambda finding: (
            finding.get("action_priority", "p9"),
            finding.get("severity", "unknown"),
            finding.get("category", ""),
        ),
    )[:5]
    domain_counts = {}
    for finding in all_findings:
        domain = finding.get("domain", "unknown")
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    priority_counts = {}
    for finding in all_findings:
        priority = finding.get("action_priority", "unknown")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1
    return {
        "headline": report.get("headline", "Infrastructure Review Summary"),
        "primary_candidate": report.get("primary_candidate", "None"),
        "recommended_action": report.get("recommended_action", "No action suggested."),
        "snapshot_findings": snapshot_findings,
        "trend_findings": trend_findings,
        "top_findings": top_findings,
        "domain_counts": domain_counts,
        "priority_counts": priority_counts,
        "quality_summary": quality_report.get("summary", {}),
        "trend_summary": summary,
    }


def build_fallback_email(context):
    snapshot_count = len(context["snapshot_findings"])
    trend_count = len(context["trend_findings"])
    quality_summary = context["quality_summary"]
    trend_summary = context["trend_summary"]
    domain_counts = context.get("domain_counts", {})
    priority_counts = context.get("priority_counts", {})
    subject = (
        f"FinOps AI Agent Report: {context['headline']}"
        if context["headline"]
        else "FinOps AI Agent Report"
    )

    lines = [
        "FinOps AI Agent Daily Summary",
        "",
        f"Headline: {context['headline']}",
        f"Primary candidate: {context['primary_candidate']}",
        f"Recommended action: {context['recommended_action']}",
        "",
        f"Snapshot findings: {snapshot_count}",
        f"Trend findings: {trend_count}",
        (
            "Trend-ready instances: "
            f"{trend_summary.get('trend_ready_instances', 0)}"
        ),
        (
            "Persistent low-utilization instances: "
            f"{trend_summary.get('persistent_low_utilization_instances', 0)}"
        ),
        (
            "Idle-but-expensive instances: "
            f"{trend_summary.get('idle_but_expensive_instances', 0)}"
        ),
        "",
        "Domain breakdown:",
        f"- finops: {domain_counts.get('finops', 0)}",
        f"- sre: {domain_counts.get('sre', 0)}",
        f"- governance: {domain_counts.get('governance', 0)}",
        "",
        "Priority breakdown:",
        f"- p1: {priority_counts.get('p1', 0)}",
        f"- p2: {priority_counts.get('p2', 0)}",
        f"- p3: {priority_counts.get('p3', 0)}",
        f"- p4: {priority_counts.get('p4', 0)}",
        "",
        "Quality summary:",
        f"- pass: {quality_summary.get('pass', 0)}",
        f"- warn: {quality_summary.get('warn', 0)}",
        f"- fail: {quality_summary.get('fail', 0)}",
        f"- info: {quality_summary.get('info', 0)}",
    ]

    top_findings = context.get("top_findings", [])
    if top_findings:
        lines.append("")
        lines.append("Top findings:")
        for finding in top_findings:
            lines.append(
                f"- [{finding.get('action_priority', 'unknown')}] "
                f"[{finding.get('domain', 'unknown')}] "
                f"{finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')} "
                f"(owner: {finding.get('recommended_owner', 'unknown')}, human-review: {finding.get('needs_human_review', True)})"
            )

    plain_text = "\n".join(lines) + "\n"
    html = build_html_email(subject, lines, top_findings)
    return {
        "subject": subject,
        "plain_text": plain_text,
        "html": html,
        "mode": "deterministic",
    }


def build_html_email(subject, lines, top_findings):
    escaped_lines = "".join(f"<p>{line}</p>" if line else "<br>" for line in lines)
    top_findings_html = ""
    if top_findings:
        items = "".join(
            "<li>"
            f"[{finding.get('action_priority', 'unknown')}] "
            f"[{finding.get('domain', 'unknown')}] "
            f"{finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')} "
            f"(owner: {finding.get('recommended_owner', 'unknown')})"
            "</li>"
            for finding in top_findings
        )
        top_findings_html = f"<h2>Top Findings</h2><ul>{items}</ul>"

    return (
        "<html><body>"
        f"<h1>{subject}</h1>"
        f"{escaped_lines}"
        f"{top_findings_html}"
        "</body></html>"
    )


def build_gemini_email_prompt(context):
    return f"""
You are an infrastructure operations assistant writing an email notification for a cloud operations report.

Return JSON with exactly these keys:
- subject
- plain_text
- html

Requirements:
- subject should be concise, specific, and action-oriented
- plain_text should read like a real operations email, not a raw dump
- html should be simple, valid, and readable
- include these sections in the email body:
  1. Executive Summary
  2. Top Findings
  3. Recommended Next Action
  4. Owner Hints
  5. Quality and Trend Summary
- prioritize p1 and p2 findings first
- mention domain names such as sre, finops, governance when relevant
- include owner hints when available
- keep the tone direct and operational, not marketing-style
- do not invent facts not present in the input
- if there are no findings in a section, say so briefly instead of padding

The email is for an operator or reviewer who needs to understand what happened in this run and what to do next.

Input:
{json.dumps(context, indent=2)}
""".strip()


def generate_gemini_email(context):
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
            "contents": [{"parts": [{"text": build_gemini_email_prompt(context)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "plain_text": {"type": "string"},
                        "html": {"type": "string"},
                    },
                    "required": ["subject", "plain_text", "html"],
                },
            },
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = json.loads(extract_gemini_text(response.json()))
    payload["mode"] = f"gemini:{model}"
    return payload


def write_email_outputs(payload):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    with open(EMAIL_JSON_PATH, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=4)
    with open(EMAIL_TXT_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write(payload["plain_text"])
    with open(EMAIL_HTML_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write(payload["html"])


def send_email(payload):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")
    if not all([smtp_host, smtp_port, email_from, email_to]):
        return False, "SMTP configuration not complete; preview files written only."

    message = EmailMessage()
    message["Subject"] = payload["subject"]
    message["From"] = email_from
    message["To"] = email_to
    message.set_content(payload["plain_text"])
    message.add_alternative(payload["html"], subtype="html")

    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

    with smtplib.SMTP(smtp_host, int(smtp_port), timeout=30) as smtp:
        smtp.ehlo()
        if use_tls:
            smtp.starttls()
            smtp.ehlo()
        if smtp_username and smtp_password:
            smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)
    return True, f"Email sent to {email_to}"


def main():
    load_env_from_file()
    report = load_json(REPORT_JSON_PATH)
    quality_report = load_json(QUALITY_JSON_PATH)
    trend_analysis = load_json(TREND_JSON_PATH)
    recommendations = load_json(RECOMMENDATIONS_JSON_PATH)
    context = build_email_context(report, quality_report, trend_analysis, recommendations)

    payload = None
    try:
        payload = generate_gemini_email(context)
    except requests.RequestException as exc:
        print(f"Gemini email generation failed, using deterministic fallback: {exc}")
    except json.JSONDecodeError as exc:
        print(f"Gemini returned non-JSON email output, using deterministic fallback: {exc}")

    if payload is None:
        payload = build_fallback_email(context)

    write_email_outputs(payload)
    sent, message = send_email(payload)
    print(
        f"Email preview written: {EMAIL_JSON_PATH.name}, {EMAIL_TXT_PATH.name}, {EMAIL_HTML_PATH.name} [{payload['mode']}]"
    )
    print(message)


if __name__ == "__main__":
    main()

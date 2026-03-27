import json
import os
import smtplib
import subprocess
from email.message import EmailMessage
from pathlib import Path

import requests

from summarizer import extract_gemini_text, load_env_from_file, load_json


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORT_JSON_PATH = OUTPUTS_DIR / "finops_report.json"
REPORT_MD_PATH = OUTPUTS_DIR / "finops_report.md"
REPORT_PDF_PATH = OUTPUTS_DIR / "finops_report.pdf"
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
    findings_by_domain = {"sre": [], "finops": [], "governance": []}
    for finding in all_findings:
        findings_by_domain.setdefault(finding["domain"], []).append(finding)
    action_items = top_findings[:3]
    highest_priority = next(
        (
            priority
            for priority in ("p1", "p2", "p3", "p4")
            if priority_counts.get(priority, 0) > 0
        ),
        "none",
    )
    grounding = report.get("grounding", {})
    grounding_evidence = grounding.get("evidence", [])
    source_references = []
    source_lookup = {}
    seen_source_ids = set()
    for item in grounding_evidence:
        source_id = item.get("id")
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        source_item = {
            "id": source_id,
            "title": item.get("title", "unknown"),
            "source": item.get("source", ""),
            "topic": item.get("topic", "unknown"),
            "score": item.get("score"),
        }
        source_references.append(source_item)
        source_lookup[source_id] = source_item

    def resolve_source_list(ids):
        return [source_lookup[source_id] for source_id in ids if source_id in source_lookup]

    evidence_mapping = {
        "why_it_matters": resolve_source_list(report.get("why_it_matters_evidence", [])),
        "recommended_action": resolve_source_list(report.get("recommended_action_evidence", [])),
        "decision_rule": resolve_source_list(report.get("decision_rule_evidence", [])),
    }
    return {
        "headline": report.get("headline", "Infrastructure Review Summary"),
        "primary_candidate": report.get("primary_candidate", "None"),
        "recommended_action": report.get("recommended_action", "No action suggested."),
        "snapshot_findings": snapshot_findings,
        "trend_findings": trend_findings,
        "top_findings": top_findings,
        "domain_counts": domain_counts,
        "priority_counts": priority_counts,
        "findings_by_domain": findings_by_domain,
        "action_items": action_items,
        "highest_priority": highest_priority,
        "quality_summary": quality_report.get("summary", {}),
        "trend_summary": summary,
        "grounding": grounding,
        "source_references": source_references,
        "evidence_mapping": evidence_mapping,
        "why_it_matters_evidence": report.get("why_it_matters_evidence", []),
        "recommended_action_evidence": report.get("recommended_action_evidence", []),
        "decision_rule_evidence": report.get("decision_rule_evidence", []),
    }


def build_fallback_email(context):
    snapshot_count = len(context["snapshot_findings"])
    trend_count = len(context["trend_findings"])
    quality_summary = context["quality_summary"]
    trend_summary = context["trend_summary"]
    domain_counts = context.get("domain_counts", {})
    priority_counts = context.get("priority_counts", {})
    source_references = context.get("source_references", [])
    evidence_mapping = context.get("evidence_mapping", {})
    subject = build_fallback_subject(context)
    lines = [
        "Cloud Operations Notification",
        "",
        "Executive Summary",
        (
            f"This run produced {snapshot_count} snapshot finding(s) and {trend_count} trend finding(s). "
            f"Highest priority observed: {context.get('highest_priority', 'none').upper()}."
        ),
        f"Headline: {context['headline']}",
        f"Primary candidate: {context['primary_candidate']}",
        "",
        "Action Items",
    ]

    action_items = context.get("action_items", [])
    if action_items:
        for finding in action_items:
            lines.append(
                f"- [{finding.get('action_priority', 'unknown').upper()}] "
                f"{finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')}: "
                f"{finding.get('summary', '')} "
                f"(owner: {finding.get('recommended_owner', 'unknown')}, human-review: {finding.get('needs_human_review', True)})"
            )
    else:
        lines.append("- No immediate action items were identified in this run.")

    lines.extend(
        [
            "",
            "Findings by Domain",
        ]
    )
    findings_by_domain = context.get("findings_by_domain", {})
    for domain in ("sre", "finops", "governance"):
        lines.append(f"- {domain}: {domain_counts.get(domain, 0)}")
        domain_findings = findings_by_domain.get(domain, [])[:3]
        if domain_findings:
            for finding in domain_findings:
                lines.append(
                    f"  {finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')} "
                    f"[{finding.get('action_priority', 'unknown')}]"
                )
        else:
            lines.append("  none")

    lines.extend(
        [
            "",
            "Recommended Next Action",
            context["recommended_action"],
            "",
            "Owner Hints",
        ]
    )
    owner_hints = {item.get("recommended_owner", "unknown") for item in action_items if item.get("recommended_owner")}
    if owner_hints:
        for owner in sorted(owner_hints):
            lines.append(f"- {owner}")
    else:
        lines.append("- No owner-specific routing was generated in this run.")

    lines.extend(
        [
            "",
            "Quality and Trend Summary",
            f"- Quality checks: pass={quality_summary.get('pass', 0)}, warn={quality_summary.get('warn', 0)}, fail={quality_summary.get('fail', 0)}, info={quality_summary.get('info', 0)}",
            f"- Trend-ready instances: {trend_summary.get('trend_ready_instances', 0)}",
            f"- Persistent low-utilization instances: {trend_summary.get('persistent_low_utilization_instances', 0)}",
            f"- Idle-but-expensive instances: {trend_summary.get('idle_but_expensive_instances', 0)}",
            f"- Domain counts: sre={domain_counts.get('sre', 0)}, finops={domain_counts.get('finops', 0)}, governance={domain_counts.get('governance', 0)}",
            f"- Priority counts: p1={priority_counts.get('p1', 0)}, p2={priority_counts.get('p2', 0)}, p3={priority_counts.get('p3', 0)}, p4={priority_counts.get('p4', 0)}",
        ]
    )
    lines.extend(
        [
            "",
            "Reference Sources",
        ]
    )
    if source_references:
        for item in source_references:
            score_suffix = f" | score={item['score']}" if item.get("score") is not None else ""
            lines.append(
                f"- {item.get('title', 'unknown')} [{item.get('topic', 'unknown')}] | {item.get('source', '')}{score_suffix}"
            )
    else:
        lines.append("- No grounded source references were attached to this run.")

    lines.extend(
        [
            "",
            "Conclusion to Source Mapping",
        ]
    )
    mapping_labels = [
        ("Why It Matters", "why_it_matters"),
        ("Recommended Action", "recommended_action"),
        ("Decision Rule", "decision_rule"),
    ]
    has_mapping = False
    for label, key in mapping_labels:
        refs = evidence_mapping.get(key, [])
        if refs:
            has_mapping = True
            lines.append(f"- {label}:")
            for item in refs:
                score_suffix = f" | score={item['score']}" if item.get("score") is not None else ""
                lines.append(
                    f"  {item.get('title', 'unknown')} | {item.get('source', '')}{score_suffix}"
                )
    if not has_mapping:
        lines.append("- No conclusion-specific source mapping was attached to this run.")

    plain_text = "\n".join(lines) + "\n"
    html = build_html_email(subject, context)
    return {
        "subject": subject,
        "plain_text": plain_text,
        "html": html,
        "mode": "deterministic",
    }


def build_fallback_subject(context):
    highest_priority = context.get("highest_priority", "none").upper()
    if highest_priority in {"P1", "P2"}:
        return f"Action Required: {context['headline']}"
    return f"Daily Cloud Ops Summary: {context['headline']}"


def build_html_email(subject, context):
    action_items = context.get("action_items", [])
    findings_by_domain = context.get("findings_by_domain", {})
    quality_summary = context.get("quality_summary", {})
    trend_summary = context.get("trend_summary", {})
    domain_counts = context.get("domain_counts", {})
    source_references = context.get("source_references", [])
    evidence_mapping = context.get("evidence_mapping", {})

    action_items_html = "".join(
        "<li>"
        f"<strong>[{finding.get('action_priority', 'unknown').upper()}]</strong> "
        f"{finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')}: "
        f"{finding.get('summary', '')} "
        f"<br><small>owner: {finding.get('recommended_owner', 'unknown')} | human-review: {finding.get('needs_human_review', True)}</small>"
        "</li>"
        for finding in action_items
    ) or "<li>No immediate action items were identified in this run.</li>"

    domain_sections = []
    for domain in ("sre", "finops", "governance"):
        items = findings_by_domain.get(domain, [])[:3]
        item_html = "".join(
            "<li>"
            f"{finding.get('instance_name', 'unknown')} / {finding.get('category', 'unknown')} "
            f"<small>[{finding.get('action_priority', 'unknown')}]</small>"
            "</li>"
            for finding in items
        ) or "<li>none</li>"
        domain_sections.append(
            f"<h3>{domain.upper()} ({domain_counts.get(domain, 0)})</h3><ul>{item_html}</ul>"
        )

    owner_hints = sorted(
        {item.get("recommended_owner", "unknown") for item in action_items if item.get("recommended_owner")}
    )
    owner_html = "".join(f"<li>{owner}</li>" for owner in owner_hints) or "<li>No owner-specific routing was generated in this run.</li>"
    source_html = "".join(
        "<li>"
        f"<a href=\"{item.get('source', '#')}\">{item.get('title', 'unknown')}</a> "
        f"<small>[{item.get('topic', 'unknown')}]"
        + (f" score={item.get('score')}" if item.get("score") is not None else "")
        + "</small>"
        "</li>"
        for item in source_references
    ) or "<li>No grounded source references were attached to this run.</li>"
    mapping_sections = []
    for label, key in (
        ("Why It Matters", "why_it_matters"),
        ("Recommended Action", "recommended_action"),
        ("Decision Rule", "decision_rule"),
    ):
        refs = evidence_mapping.get(key, [])
        if refs:
            item_html = "".join(
                "<li>"
                f"<a href=\"{item.get('source', '#')}\">{item.get('title', 'unknown')}</a> "
                f"<small>[{item.get('topic', 'unknown')}]"
                + (f" score={item.get('score')}" if item.get("score") is not None else "")
                + "</small>"
                "</li>"
                for item in refs
            )
            mapping_sections.append(f"<h3>{label}</h3><ul>{item_html}</ul>")
    mapping_html = "".join(mapping_sections) or "<p>No conclusion-specific source mapping was attached to this run.</p>"

    return f"""
<html>
  <body style="font-family: Arial, sans-serif; color: #1f2937; line-height: 1.5;">
    <h1>{subject}</h1>
    <h2>Executive Summary</h2>
    <p>
      This run produced {len(context.get('snapshot_findings', []))} snapshot finding(s) and
      {len(context.get('trend_findings', []))} trend finding(s).
      Highest priority observed: {context.get('highest_priority', 'none').upper()}.
    </p>
    <p><strong>Headline:</strong> {context.get('headline', '')}</p>
    <p><strong>Primary candidate:</strong> {context.get('primary_candidate', '')}</p>

    <h2>Action Items</h2>
    <ul>{action_items_html}</ul>

    <h2>Findings by Domain</h2>
    {''.join(domain_sections)}

    <h2>Recommended Next Action</h2>
    <p>{context.get('recommended_action', '')}</p>

    <h2>Owner Hints</h2>
    <ul>{owner_html}</ul>

    <h2>Quality and Trend Summary</h2>
    <ul>
      <li>Quality checks: pass={quality_summary.get('pass', 0)}, warn={quality_summary.get('warn', 0)}, fail={quality_summary.get('fail', 0)}, info={quality_summary.get('info', 0)}</li>
      <li>Trend-ready instances: {trend_summary.get('trend_ready_instances', 0)}</li>
      <li>Persistent low-utilization instances: {trend_summary.get('persistent_low_utilization_instances', 0)}</li>
      <li>Idle-but-expensive instances: {trend_summary.get('idle_but_expensive_instances', 0)}</li>
    </ul>

    <h2>Reference Sources</h2>
    <ul>{source_html}</ul>

    <h2>Conclusion to Source Mapping</h2>
    {mapping_html}
  </body>
</html>
""".strip()


def build_gemini_email_prompt(context):
    return f"""
You are an infrastructure operations assistant writing an email notification for a cloud operations report.

Return JSON with exactly these keys:
- subject
- plain_text
- html

Requirements:
- subject should be concise, specific, and action-oriented
- plain_text should read like a real operations email with stable section headers
- html should follow the same section structure as the plain text version
- include these sections in the email body:
  1. Executive Summary
  2. Action Items
  3. Findings by Domain
  4. Recommended Next Action
  5. Owner Hints
  6. Quality and Trend Summary
  7. Reference Sources
  8. Conclusion to Source Mapping
- prioritize p1 and p2 findings first
- mention domain names such as sre, finops, governance when relevant
- include owner hints when available
- keep the tone direct and operational, not marketing-style
- use the provided grounding evidence when you explain platform-specific behavior or remediation steps
- prefer grounded explanations over generic cloud advice
- do not invent facts not present in the input
- do not add any system state, owner, root cause, dependency, or business impact unless it is explicitly present in the input
- do not imply a recommendation was generated if it was not present in the input
- if something is uncertain, frame it as a review item or a possibility to verify
- never present assumptions as confirmed facts
- if there are no findings in a section, say so briefly instead of padding
- for Findings by Domain, group items under sre, finops, and governance
- for Reference Sources, list the grounded source title and a directly usable URL when grounding evidence is present
- for Conclusion to Source Mapping, explicitly show which sources support Why It Matters, Recommended Action, and Decision Rule
- do not cite any external document or practice unless it appears in the grounding evidence contained in the input
- do not output markdown fences or explanations outside the JSON object

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


def markdown_line_to_html(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if text.startswith("### "):
        return f"<b>{text[4:].strip()}</b>"
    if text.startswith("## "):
        return f"<b>{text[3:].strip()}</b>"
    if text.startswith("# "):
        return f"<b>{text[2:].strip()}</b>"
    if text.startswith("- "):
        return f"&bull; {text[2:].strip()}"
    return text


def render_report_pdf() -> Path:
    OUTPUTS_DIR.mkdir(exist_ok=True)
    script = r"""
from pathlib import Path
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

md_path = Path(sys.argv[1])
pdf_path = Path(sys.argv[2])

def markdown_line_to_html(line: str) -> str:
    text = line.strip()
    if not text:
        return ""
    if text.startswith("### "):
        return f"<b>{text[4:].strip()}</b>"
    if text.startswith("## "):
        return f"<b>{text[3:].strip()}</b>"
    if text.startswith("# "):
        return f"<b>{text[2:].strip()}</b>"
    if text.startswith("- "):
        return f"&bull; {text[2:].strip()}"
    return text

markdown_text = md_path.read_text(encoding="utf-8")
doc = SimpleDocTemplate(
    str(pdf_path),
    pagesize=letter,
    leftMargin=0.75 * inch,
    rightMargin=0.75 * inch,
    topMargin=0.75 * inch,
    bottomMargin=0.75 * inch,
)
styles = getSampleStyleSheet()
body_style = ParagraphStyle(
    "ReportBody",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=10,
    leading=14,
    spaceAfter=6,
)
story = []
for raw_line in markdown_text.splitlines():
    html_line = markdown_line_to_html(raw_line)
    if not html_line:
        story.append(Spacer(1, 0.12 * inch))
        continue
    story.append(Paragraph(html_line, body_style))
doc.build(story)
print(pdf_path)
"""
    subprocess.run(
        ["python3", "-c", script, str(REPORT_MD_PATH), str(REPORT_PDF_PATH)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return REPORT_PDF_PATH


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
    if REPORT_MD_PATH.is_file():
        pdf_path = render_report_pdf()
        message.add_attachment(
            pdf_path.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename=pdf_path.name,
        )

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
    if REPORT_MD_PATH.is_file():
        pdf_path = render_report_pdf()
        payload["report_pdf_path"] = str(pdf_path)
        with open(EMAIL_JSON_PATH, "w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, indent=4)
    sent, message = send_email(payload)
    print(
        f"Email preview written: {EMAIL_JSON_PATH.name}, {EMAIL_TXT_PATH.name}, {EMAIL_HTML_PATH.name} [{payload['mode']}]"
    )
    print(message)


if __name__ == "__main__":
    main()

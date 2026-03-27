import re
from html import unescape
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"
ARTICLE_DIR = BASE_DIR / "article"
SUPPORTED_DOC_IDS = {
    "bigquery-datasets",
    "compute-labels",
    "compute-machine-types",
    "compute-machine-types-overview",
    "gcp-metrics-catalog",
    "ops-agent-installation",
    "ops-agent-overview",
}

START_END_PATTERNS = [
    (r'<div class="devsite-article-body clearfix.*?">', r"<devsite-content-footer"),
    (r'<main role="main" id="main-content".*?>', r"<devsite-content-footer"),
]

DROP_EXACT = {
    "Skip to main content",
    "Technology areas",
    "close",
    "Console",
    "English",
    "Sign in",
    "Start free",
    "More",
    "Discover",
    "Before you begin",
    "On this page",
    "Send feedback",
    "Registry",
    "Terraform Registry",
    "Please enable Javascript to use this application",
}

DROP_PREFIXES = (
    "Google Cloud Documentation",
    "Google Cloud Observability",
    "Compute Engine | Google Cloud Documentation",
    "Google Cloud console",
    "For more information, see",
    "This page describes",
)

DROP_CONTAINS = (
    "Español",
    "Français",
    "Deutsch",
    "Português",
    "日本語",
    "한국어",
    "中文",
    "עברית",
    "Indonesia",
    "Italiano",
    "América Latina",
    "Google Cloud Documentation",
    "devsite",
)

DROP_SINGLE_TOKEN = {
    "Overview",
    "Guides",
    "Reference",
    "Resources",
    "APIs",
    "Compute",
    "Storage",
    "Networking",
    "Security",
    "Migration",
}

SECTION_RULES = {
    "compute-labels": {
        "start_line": "What are labels?",
        "end_line": "What's next",
    },
    "compute-machine-types": {
        "start_line": "This document describes the machine families, machine series, and machine types",
        "end_line": "What's next",
    },
    "compute-machine-types-overview": {
        "start_line": "This document describes the machine families, machine series, and machine types",
        "end_line": "What's next",
    },
    "bigquery-datasets": {
        "start_line": "Create datasets",
        "end_line": "What's next",
    },
    "ops-agent-installation": {
        "start_line": "The Ops Agent collects logs and metrics on Compute Engine instances, sending",
        "end_line": "What's next",
    },
    "ops-agent-overview": {
        "start_line": "The Ops Agent is the primary agent for collecting telemetry from your",
        "end_line": "What's next",
    },
    "gcp-metrics-catalog": {
        "start_line": "compute",
    },
}


def extract_article_body(html: str) -> str:
    for start_pattern, end_pattern in START_END_PATTERNS:
        start = re.search(start_pattern, html, flags=re.IGNORECASE | re.DOTALL)
        end = re.search(end_pattern, html, flags=re.IGNORECASE | re.DOTALL)
        if start and end and start.start() < end.start():
            return html[start.start() : end.start()]
    return html


def strip_html(html: str) -> list[str]:
    body = re.sub(r"<script.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.DOTALL)
    body = re.sub(
        r"<(h1|h2|h3|h4|h5|h6|p|li|pre|code|table|tr|td|th|section|article|div|ul|ol|br)[^>]*>",
        "\n",
        body,
        flags=re.IGNORECASE,
    )
    body = re.sub(r"<[^>]+>", " ", body)
    body = unescape(body)

    lines = []
    for raw_line in body.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return lines


def is_noise(line: str) -> bool:
    if line in DROP_EXACT or line in DROP_SINGLE_TOKEN:
        return True
    if any(line.startswith(prefix) for prefix in DROP_PREFIXES):
        return True
    if any(token in line for token in DROP_CONTAINS):
        return True
    if len(line) <= 2:
        return True
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9 _/\-]{0,20}", line) and line.count(" ") <= 2 and line.istitle():
        return True
    return False


def compact_lines(lines: list[str]) -> list[str]:
    filtered: list[str] = []
    previous = None
    for line in lines:
        if is_noise(line):
            continue
        if previous == line:
            continue
        filtered.append(line)
        previous = line
    return filtered


def clean_file(html_path: Path) -> str:
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = unescape(title_match.group(1)).strip() if title_match else html_path.stem
    article_body = extract_article_body(html)
    lines = strip_html(article_body)
    filtered = compact_lines(lines)
    pruned = prune_sections(html_path.stem, filtered)
    return f"# {title}\n\nSource file: {html_path.name}\n\n" + "\n\n".join(pruned) + "\n"


def prune_sections(doc_id: str, lines: list[str]) -> list[str]:
    if doc_id not in SECTION_RULES:
        return lines

    rule = SECTION_RULES[doc_id]
    start_line = rule.get("start_line")
    end_line = rule.get("end_line")

    start_idx = 0
    end_idx = len(lines)

    if start_line:
        for i, line in enumerate(lines):
            if line == start_line:
                start_idx = i
                break

    if end_line:
        for i in range(start_idx, len(lines)):
            if lines[i] == end_line:
                end_idx = i
                break

    result = [line.strip() for line in lines[start_idx:end_idx] if line.strip()]
    return result or lines


def main() -> None:
    ARTICLE_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for html_path in sorted(RAW_DIR.glob("*.html")):
        if html_path.stem not in SUPPORTED_DOC_IDS:
            continue
        cleaned = clean_file(html_path)
        out_path = ARTICLE_DIR / f"{html_path.stem}.txt"
        out_path.write_text(cleaned, encoding="utf-8")
        written.append(out_path)

    print("cleaned files:")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()

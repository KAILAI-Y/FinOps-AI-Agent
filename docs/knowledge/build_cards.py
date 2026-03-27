import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ARTICLE_DIR = BASE_DIR / "article"
CARDS_DIR = BASE_DIR / "cards"
CARDS_JSON = CARDS_DIR / "knowledge_cards.json"
CARDS_JSONL = CARDS_DIR / "knowledge_cards.jsonl"


DOC_CONFIG = {
    "compute-labels": {
        "topic": "labels",
        "source": "https://cloud.google.com/compute/docs/labeling-resources",
        "usage": ["governance", "owner-labels", "cost-center-labels"],
        "headings": [
            "What are labels?",
            "Requirements for labels",
            "Common uses of labels",
            "Labels and tags",
            "Use labels on Compute Engine",
            "Create resources with labels",
            "Add or update labels to existing resources",
            "View labels",
            "Get a label fingerprint for API requests",
            "Remove a label",
            "Filter searches using labels",
            "Relationship between VM labels and tags",
        ],
        "section_splits": {
            "Create resources with labels": [
                {"title": "Create resources with labels - console", "section": "create-resources-with-labels-console", "start": "Go to the resource page that you want to create.", "end": "gcloud"},
                {"title": "Create resources with labels - gcloud", "section": "create-resources-with-labels-gcloud", "start": "gcloud", "end": "REST"},
                {"title": "Create resources with labels - REST", "section": "create-resources-with-labels-rest", "start": "REST"},
            ],
            "Add or update labels to existing resources": [
                {"title": "Add or update labels - console", "section": "add-update-labels-console", "start": "Go to the resource page for which you want to add labels.", "end": "gcloud"},
                {"title": "Add or update labels - gcloud", "section": "add-update-labels-gcloud", "start": "gcloud", "end": "REST"},
                {"title": "Add or update labels - REST", "section": "add-update-labels-rest", "start": "REST"},
            ],
            "View labels": [
                {"title": "View labels - console", "section": "view-labels-console", "start": "You can view labels for resources by using the Google Cloud console, the", "end": "gcloud"},
                {"title": "View labels - gcloud", "section": "view-labels-gcloud", "start": "gcloud", "end": "REST"},
                {"title": "View labels - REST", "section": "view-labels-rest", "start": "REST"},
            ],
            "Remove a label": [
                {"title": "Remove a label - console", "section": "remove-label-console", "start": "You can remove labels from resources by using the Google Cloud console, the", "end": "gcloud"},
                {"title": "Remove a label - gcloud", "section": "remove-label-gcloud", "start": "gcloud", "end": "REST"},
                {"title": "Remove a label - REST", "section": "remove-label-rest", "start": "REST"},
            ],
            "Filter searches using labels": [
                {"title": "Filter searches using labels - console", "section": "filter-labels-console", "start": "You can search your resources and filter results by labels by using the", "end": "gcloud"},
                {"title": "Filter searches using labels - gcloud", "section": "filter-labels-gcloud", "start": "gcloud", "end": "REST"},
                {"title": "Filter searches using labels - REST", "section": "filter-labels-rest", "start": "REST"},
            ],
        },
    },
    "compute-machine-types": {
        "topic": "machine-types",
        "source": "https://cloud.google.com/compute/docs/machine-resource",
        "usage": ["rightsizing", "machine-type-selection", "terraform-machine-type"],
        "headings": [
            "Compute Engine terminology",
            "Predefined machine types",
            "Local SSD machine types",
            "Bare metal machine types",
            "Custom machine types",
            "Shared-core machine types",
            "General-purpose machine family guide",
            "Compute-optimized machine family guide",
            "Memory-optimized machine family guide",
            "Accelerator-optimized machine family guide",
        ],
    },
    "ops-agent-installation": {
        "topic": "ops-agent",
        "source": "https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/installation",
        "usage": ["missing-observability", "memory-metrics", "agent-installation"],
        "headings": [
            "Install the agent automatically during VM creation",
            "Install the agent from the command line",
            "Install the latest version of the agent",
            "Installing a specific version of the agent",
            "VMs without remote package access",
        ],
        "section_splits": {
            "Install the latest version of the agent": [
                {"title": "Install latest Ops Agent - Linux", "section": "install-latest-linux", "start": "To install the latest version of the agent, complete the following steps.", "end": "Connect to your instance using RDP or a similar tool and login to Windows."},
                {"title": "Install latest Ops Agent - Windows", "section": "install-latest-windows", "start": "Connect to your instance using RDP or a similar tool and login to Windows."},
            ],
            "Installing a specific version of the agent": [
                {"title": "Install specific Ops Agent version - Linux", "section": "install-specific-linux", "start": "To install a specific version of the agent, complete the following steps.", "end": "Connect to your instance using RDP or a similar tool and login to Windows."},
                {"title": "Install specific Ops Agent version - Windows", "section": "install-specific-windows", "start": "Connect to your instance using RDP or a similar tool and login to Windows."},
            ],
        },
    },
    "ops-agent-overview": {
        "topic": "ops-agent",
        "source": "https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent",
        "usage": ["missing-observability", "memory-metrics", "ops-agent-capabilities"],
        "headings": [
            "Ops Agent features",
            "Logging features",
            "Third-party application support",
            "Monitoring features",
        ],
    },
    "bigquery-datasets": {
        "topic": "bigquery-datasets",
        "source": "https://cloud.google.com/bigquery/docs/datasets",
        "usage": ["bigquery-export", "dataset-setup", "dataset-governance"],
        "headings": [
            "Create datasets",
            "Dataset limitations",
            "Required permissions",
            "Hidden datasets",
            "Dataset security",
        ],
        "section_splits": {
            "Create datasets": [
                {"title": "Create datasets - console", "section": "create-datasets-console", "start": "Open the BigQuery page in the Google Cloud console.", "end": "SQL"},
                {"title": "Create datasets - SQL", "section": "create-datasets-sql", "start": "SQL", "end": "bq mk command"},
                {"title": "Create datasets - bq", "section": "create-datasets-bq", "start": "bq mk command", "end": "To apply your Terraform configuration in a Google Cloud project, complete the steps in the"},
                {"title": "Create datasets - Terraform", "section": "create-datasets-terraform", "start": "To apply your Terraform configuration in a Google Cloud project, complete the steps in the", "end": "datasets.insert"},
                {"title": "Create datasets - API", "section": "create-datasets-api", "start": "datasets.insert", "end": "client libraries ."},
                {"title": "Create datasets - client libraries", "section": "create-datasets-client-libraries", "start": "client libraries ."},
            ],
        },
    },
}

MAX_CARD_CHARS = 1400
TERMINAL_MARKER_PARAGRAPHS = {"gcloud", "REST", "SQL", "API"}


METRIC_CARDS = [
    {
        "section": "instance-cpu-guest-visible-vcpus",
        "metric_name": "instance/cpu/guest_visible_vcpus",
        "title": "Compute Engine guest-visible vCPUs",
        "usage": ["shared-core-vms", "machine-type-context", "cpu-interpretation"],
    },
    {
        "section": "instance-cpu-reserved-cores",
        "metric_name": "instance/cpu/reserved_cores",
        "title": "Compute Engine reserved CPU cores",
        "usage": ["shared-core-vms", "cpu-interpretation", "rightsizing"],
    },
    {
        "section": "guest-cpu-usage-time",
        "metric_name": "guest/cpu/usage_time",
        "title": "Guest CPU usage time metric",
        "usage": ["cpu-metrics", "guest-metrics", "ops-agent-context"],
    },
    {
        "section": "instance-cpu-utilization",
        "metric_name": "instance/cpu/utilization",
        "title": "Compute Engine CPU utilization metric",
        "usage": ["cpu-metrics", "rightsizing", "snapshot-analysis"],
    },
    {
        "section": "guest-disk-bytes-used",
        "metric_name": "guest/disk/bytes_used",
        "title": "Guest disk bytes used metric",
        "usage": ["disk-capacity", "guest-metrics", "ops-agent-context"],
    },
    {
        "section": "instance-disk-read-bytes",
        "metric_name": "instance/disk/read_bytes_count",
        "title": "Compute Engine disk read bytes metric",
        "usage": ["disk-activity", "throughput", "snapshot-analysis"],
    },
    {
        "section": "instance-network-sent-bytes",
        "metric_name": "instance/network/sent_bytes_count",
        "title": "Compute Engine network sent bytes metric",
        "usage": ["network-activity", "throughput", "snapshot-analysis"],
    },
    {
        "section": "instance-uptime",
        "metric_name": "instance/uptime",
        "title": "Compute Engine uptime delta metric",
        "usage": ["lifecycle", "uptime", "snapshot-analysis"],
    },
    {
        "section": "instance-uptime-total",
        "metric_name": "instance/uptime_total",
        "title": "Compute Engine uptime total metric",
        "usage": ["lifecycle", "uptime", "instance-age"],
    },
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def read_article(doc_id: str) -> tuple[str, list[str]]:
    path = ARTICLE_DIR / f"{doc_id}.txt"
    text = path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in text.splitlines()]
    title = lines[0].lstrip("# ").strip()
    body_text = "\n".join(lines[3:]).strip()
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", body_text) if paragraph.strip()]
    return title, paragraphs


def normalize_text(paragraphs: list[str]) -> str:
    text = "\n\n".join(paragraphs)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def trim_terminal_marker_paragraphs(paragraphs: list[str]) -> list[str]:
    trimmed = list(paragraphs)
    while trimmed and trimmed[-1].strip() in TERMINAL_MARKER_PARAGRAPHS:
        trimmed.pop()
    return trimmed


def chunk_paragraphs(paragraphs: list[str], max_chars: int = MAX_CARD_CHARS) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        addition = len(paragraph) + 2
        if current and current_len + addition > max_chars:
            chunks.append(current)
            current = [paragraph]
            current_len = addition
        else:
            current.append(paragraph)
            current_len += addition

    if current:
        chunks.append(current)
    return chunks


def build_card_payload(
    *,
    card_id: str,
    doc_id: str,
    doc_title: str,
    title: str,
    topic: str,
    section: str,
    source: str,
    usage: list[str],
    paragraphs: list[str],
) -> list[dict]:
    paragraphs = trim_terminal_marker_paragraphs(paragraphs)
    chunks = chunk_paragraphs(paragraphs)
    cards: list[dict] = []
    total_parts = len(chunks)

    for index, chunk in enumerate(chunks, 1):
        part_suffix = f"-part-{index}" if total_parts > 1 else ""
        part_title = f"{title} (part {index})" if total_parts > 1 else title
        part_section = f"{section}-part-{index}" if total_parts > 1 else section
        card = {
            "id": f"{card_id}{part_suffix}",
            "doc_id": doc_id,
            "doc_title": doc_title,
            "title": part_title,
            "topic": topic,
            "section": part_section,
            "source": source,
            "usage": usage,
            "content": normalize_text(chunk),
        }
        if total_parts > 1:
            card["part"] = index
            card["total_parts"] = total_parts
        cards.append(card)

    return cards


def find_index_by_substring(paragraphs: list[str], needle: str, start: int = 0) -> int | None:
    for i in range(start, len(paragraphs)):
        if needle in paragraphs[i]:
            return i
    return None


def find_all_indices_by_substring(paragraphs: list[str], needle: str) -> list[int]:
    return [i for i, paragraph in enumerate(paragraphs) if needle in paragraph]


def slice_by_markers(
    paragraphs: list[str],
    *,
    start: str,
    end: str | None = None,
    start_occurrence: int = 1,
) -> list[str]:
    matches = find_all_indices_by_substring(paragraphs, start)
    if len(matches) < start_occurrence:
        return []

    start_idx = matches[start_occurrence - 1]
    end_idx = len(paragraphs)
    if end:
        end_match = find_index_by_substring(paragraphs, end, start_idx + 1)
        if end_match is not None:
            end_idx = end_match
    return paragraphs[start_idx:end_idx]


def build_split_cards(
    *,
    doc_id: str,
    doc_title: str,
    topic: str,
    source: str,
    usage: list[str],
    paragraphs: list[str],
    split_specs: list[dict],
) -> list[dict]:
    cards: list[dict] = []
    positions: list[tuple[dict, int]] = []

    for spec in split_specs:
        idx = find_index_by_substring(paragraphs, spec["start"])
        if idx is not None:
            idx += spec.get("start_offset", 0)
            if idx < 0:
                idx = 0
            positions.append((spec, idx))

    positions.sort(key=lambda item: item[1])

    for i, (spec, start_idx) in enumerate(positions):
        end_idx = len(paragraphs)

        if spec.get("end"):
            end_match = find_index_by_substring(paragraphs, spec["end"], start_idx + 1)
            if end_match is not None:
                end_idx = end_match

        if i + 1 < len(positions):
            end_idx = min(end_idx, positions[i + 1][1])

        sub_paragraphs = paragraphs[start_idx:end_idx]
        if not sub_paragraphs:
            continue

        cards.extend(
            build_card_payload(
                card_id=f"{doc_id}-{spec['section']}",
                doc_id=doc_id,
                doc_title=doc_title,
                title=spec["title"],
                topic=topic,
                section=spec["section"],
                source=source,
                usage=usage,
                paragraphs=sub_paragraphs,
            )
        )

    return cards


def build_custom_split_group(
    *,
    doc_id: str,
    doc_title: str,
    topic: str,
    source: str,
    usage: list[str],
    body: list[str],
    group: dict,
) -> list[dict]:
    group_paragraphs = slice_by_markers(
        body,
        start=group["range_start"],
        end=group.get("range_end"),
        start_occurrence=group.get("range_start_occurrence", 1),
    )
    if not group_paragraphs:
        return []

    cards: list[dict] = []
    cards.extend(
        build_split_cards(
            doc_id=doc_id,
            doc_title=doc_title,
            topic=topic,
            source=source,
            usage=usage,
            paragraphs=group_paragraphs,
            split_specs=group["split_specs"],
        )
    )
    return cards


def build_compute_labels_custom_cards(doc_id: str, title: str, config: dict, body: list[str]) -> tuple[list[dict], set[str]]:
    groups = [
        {
            "skip_heading": "Create resources with labels",
            "range_start": "When creating a new resource, you can apply labels to the resource.",
            "range_end": "You can add labels or update existing labels on resources by using the",
            "split_specs": [
                {
                    "title": "Create resources with labels - console",
                    "section": "create-resources-with-labels-console",
                    "start": "Go to the resource page that you want to create.",
                    "end": "To add a label, use the",
                },
                {
                    "title": "Create resources with labels - gcloud",
                    "section": "create-resources-with-labels-gcloud",
                    "start": "To add a label, use the",
                    "end": "In the API, during the",
                },
                {
                    "title": "Create resources with labels - REST",
                    "section": "create-resources-with-labels-rest",
                    "start": "In the API, during the",
                },
            ],
        },
        {
            "skip_heading": "Add or update labels to existing resources",
            "range_start": "You can add labels or update existing labels on resources by using the",
            "range_end": "You can view labels for resources by using the Google Cloud console, the",
            "split_specs": [
                {
                    "title": "Add or update labels - console",
                    "section": "add-update-labels-console",
                    "start": "Go to the resource page for which you want to add labels.",
                    "end": "To add or change a label, use the",
                },
                {
                    "title": "Add or update labels - gcloud",
                    "section": "add-update-labels-gcloud",
                    "start": "To add or change a label, use the",
                    "end": "To add or update labels, make a",
                },
                {
                    "title": "Add or update labels - REST",
                    "section": "add-update-labels-rest",
                    "start": "To add or update labels, make a",
                },
            ],
        },
        {
            "skip_heading": "View labels",
            "range_start": "You can view labels for resources by using the Google Cloud console, the",
            "range_end": "To retrieve the fingerprint of a label, get a list of the resources and then find the",
            "split_specs": [
                {
                    "title": "View labels - console",
                    "section": "view-labels-console",
                    "start": "You can view labels for resources by using the Google Cloud console, the",
                    "end": "To view labels, use the",
                },
                {
                    "title": "View labels - gcloud",
                    "section": "view-labels-gcloud",
                    "start": "To view labels, use the",
                    "end": "To view labels directly by using the",
                },
                {
                    "title": "View labels - REST",
                    "section": "view-labels-rest",
                    "start": "To view labels directly by using the",
                },
            ],
        },
        {
            "skip_heading": "Remove a label",
            "range_start": "You can remove labels from resources by using the Google Cloud console,",
            "range_end": "You can search your resources and filter results by labels by using the",
            "split_specs": [
                {
                    "title": "Remove a label - console",
                    "section": "remove-label-console",
                    "start": "You can remove labels from resources by using the Google Cloud console,",
                    "end": "To add or change a label, use the",
                },
                {
                    "title": "Remove a label - gcloud",
                    "section": "remove-label-gcloud",
                    "start": "To add or change a label, use the",
                    "end": "To remove labels, make a",
                },
                {
                    "title": "Remove a label - REST",
                    "section": "remove-label-rest",
                    "start": "To remove labels, make a",
                },
            ],
        },
        {
            "skip_heading": "Filter searches using labels",
            "range_start": "You can search your resources and filter results by labels by using the",
            "range_end": "Relationship between VM labels and tags",
            "split_specs": [
                {
                    "title": "Filter searches using labels - console",
                    "section": "filter-labels-console",
                    "start": "You can search your resources and filter results by labels by using the",
                    "end": "To filter based on labels, use the",
                },
                {
                    "title": "Filter searches using labels - gcloud",
                    "section": "filter-labels-gcloud",
                    "start": "To filter based on labels, use the",
                    "end": "To filter resources, make a",
                },
                {
                    "title": "Filter searches using labels - REST",
                    "section": "filter-labels-rest",
                    "start": "To filter resources, make a",
                },
            ],
        },
    ]

    cards: list[dict] = []
    skipped: set[str] = set()
    for group in groups:
        cards.extend(
            build_custom_split_group(
                doc_id=doc_id,
                doc_title=title,
                topic=config["topic"],
                source=config["source"],
                usage=config["usage"],
                body=body,
                group=group,
            )
        )
        skipped.add(group["skip_heading"])
    return cards, skipped


def build_bigquery_custom_cards(doc_id: str, title: str, config: dict, body: list[str]) -> tuple[list[dict], set[str]]:
    groups = [
        {
            "skip_heading": "Create datasets",
            "range_start": "When you create a dataset, you typically specify a location where the data is",
            "range_end": "Hidden datasets",
            "split_specs": [
                {
                    "title": "Create datasets - console",
                    "section": "create-datasets-console",
                    "start": "Open the BigQuery page in the Google Cloud console.",
                    "end": "SQL",
                },
                {
                    "title": "Create datasets - SQL",
                    "section": "create-datasets-sql",
                    "start": "SQL",
                    "end": "bq mk command",
                },
                {
                    "title": "Create datasets - bq",
                    "section": "create-datasets-bq",
                    "start": "bq mk command",
                    "end": "google_bigquery_dataset",
                },
                {
                    "title": "Create datasets - Terraform",
                    "section": "create-datasets-terraform",
                    "start": "google_bigquery_dataset",
                    "start_offset": -1,
                    "end": "Call the",
                },
                {
                    "title": "Create datasets - API",
                    "section": "create-datasets-api",
                    "start": "Call the",
                    "end": "Before trying this sample, follow the C# setup instructions in the",
                },
                {
                    "title": "Create datasets - client libraries",
                    "section": "create-datasets-client-libraries",
                    "start": "Before trying this sample, follow the C# setup instructions in the",
                },
            ],
        }
    ]

    cards: list[dict] = []
    skipped: set[str] = set()
    for group in groups:
        cards.extend(
            build_custom_split_group(
                doc_id=doc_id,
                doc_title=title,
                topic=config["topic"],
                source=config["source"],
                usage=config["usage"],
                body=body,
                group=group,
            )
        )
        skipped.add(group["skip_heading"])
    return cards, skipped


def build_custom_cards(doc_id: str, title: str, config: dict, body: list[str]) -> tuple[list[dict], set[str]]:
    if doc_id == "compute-labels":
        return build_compute_labels_custom_cards(doc_id, title, config, body)
    if doc_id == "bigquery-datasets":
        return build_bigquery_custom_cards(doc_id, title, config, body)
    if doc_id == "ops-agent-installation":
        cards = build_card_payload(
            card_id=f"{doc_id}-install-the-agent-automatically-during-vm-creation",
            doc_id=doc_id,
            doc_title=title,
            title="Install the agent automatically during VM creation",
            topic=config["topic"],
            section="install-the-agent-automatically-during-vm-creation",
            source=config["source"],
            usage=config["usage"],
            paragraphs=[
                "Install the Ops Agent during VM creation.",
                "If you need to install the agent outside VM creation, use the command-line instructions in the same document.",
            ],
        )
        return cards, {"Install the agent automatically during VM creation"}
    return [], set()


def find_heading_positions(lines: list[str], headings: list[str]) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    cursor = 0
    for heading in headings:
        for i in range(cursor, len(lines)):
            if lines[i] == heading:
                found.append((heading, i))
                cursor = i + 1
                break
    return found


def build_section_cards(doc_id: str) -> list[dict]:
    title, body = read_article(doc_id)
    config = DOC_CONFIG[doc_id]
    heading_positions = find_heading_positions(body, config["headings"])
    cards: list[dict] = []
    custom_cards, skipped_headings = build_custom_cards(doc_id, title, config, body)
    cards.extend(custom_cards)

    intro_end = heading_positions[0][1] if heading_positions else len(body)
    intro_lines = body[:intro_end]
    if intro_lines:
        cards.extend(
            build_card_payload(
                card_id=f"{doc_id}-overview",
                doc_id=doc_id,
                doc_title=title,
                title=f"{title} overview",
                topic=config["topic"],
                section="overview",
                source=config["source"],
                usage=config["usage"],
                paragraphs=intro_lines,
            )
        )

    for index, (heading, start) in enumerate(heading_positions):
        if heading in skipped_headings:
            continue
        end = heading_positions[index + 1][1] if index + 1 < len(heading_positions) else len(body)
        section_paragraphs = body[start + 1 : end]
        if not section_paragraphs:
            continue
        split_specs = config.get("section_splits", {}).get(heading)
        if split_specs:
            cards.extend(
                build_split_cards(
                    doc_id=doc_id,
                    doc_title=title,
                    topic=config["topic"],
                    source=config["source"],
                    usage=config["usage"],
                    paragraphs=section_paragraphs,
                    split_specs=split_specs,
                )
            )
            continue
        cards.extend(
            build_card_payload(
                card_id=f"{doc_id}-{slugify(heading)}",
                doc_id=doc_id,
                doc_title=title,
                title=heading,
                topic=config["topic"],
                section=slugify(heading),
                source=config["source"],
                usage=config["usage"],
                paragraphs=section_paragraphs,
            )
        )

    return cards


def extract_metric_block(lines: list[str], metric_name: str) -> list[str]:
    start = None
    for i, line in enumerate(lines):
        if line == metric_name:
            start = i
            break
    if start is None:
        return []

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if "/" in lines[i] and lines[i] != metric_name and not lines[i].startswith("compute.googleapis.com/"):
            if re.fullmatch(r"[a-z0-9_./]+", lines[i]):
                end = i
                break
    return lines[start:end]


def build_metric_cards() -> list[dict]:
    doc_id = "gcp-metrics-catalog"
    title, body = read_article(doc_id)
    source = "https://cloud.google.com/monitoring/api/metrics_gcp_c"
    cards = [
        *build_card_payload(
            card_id=f"{doc_id}-compute-overview",
            doc_id=doc_id,
            doc_title=title,
            title="Compute metrics catalog overview",
            topic="gcp-compute-metrics",
            section="compute-overview",
            source=source,
            usage=["metrics-grounding", "cpu-metrics", "disk-metrics", "network-metrics"],
            paragraphs=body[:20],
        )
    ]

    for metric in METRIC_CARDS:
        block = extract_metric_block(body, metric["metric_name"])
        if not block:
            continue
        cards.extend(
            build_card_payload(
                card_id=f"{doc_id}-{metric['section']}",
                doc_id=doc_id,
                doc_title=title,
                title=metric["title"],
                topic="gcp-compute-metrics",
                section=metric["section"],
                source=source,
                usage=metric["usage"],
                paragraphs=block,
            )
        )

    return cards


def main() -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    cards: list[dict] = []

    for doc_id in DOC_CONFIG:
        cards.extend(build_section_cards(doc_id))

    cards.extend(build_metric_cards())

    CARDS_JSON.write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with CARDS_JSONL.open("w", encoding="utf-8") as handle:
        for card in cards:
            handle.write(json.dumps(card, ensure_ascii=False) + "\n")

    print(f"wrote {len(cards)} cards")
    print(CARDS_JSON)
    print(CARDS_JSONL)


if __name__ == "__main__":
    main()

import json
import os
import shutil
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from finops_agent.bigquery_writer import export_to_bigquery
from requests import exceptions as requests_exceptions
from google.cloud import compute_v1
from finops_agent.metrics import get_metric_average, get_metric_latest, get_metric_sum
from finops_agent.pricing import estimate_hourly_cost, estimate_monthly_cost
from finops_agent.rules import build_recommendations
from finops_agent.schema import VMMetric

COLOR_ENABLED = sys.stdout.isatty()
COLOR_RESET = "\033[0m"
COLOR_ACCENT = "\033[96m"
COLOR_SUCCESS = "\033[92m"
COLOR_WARN = "\033[93m"
COLOR_BOLD = "\033[1m"
BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"


def stylize(text, *effects):
    if not COLOR_ENABLED or not effects:
        return text
    prefix = "".join(effects)
    return f"{prefix}{text}{COLOR_RESET}"


def render_banner(text):
    width = shutil.get_terminal_size((80, 20)).columns
    line_len = min(max(len(text) + 4, 40), width)
    divider = "=" * line_len
    banner_body = text.center(line_len)
    return "\n".join(
        [
            stylize(divider, COLOR_ACCENT),
            stylize(banner_body, COLOR_BOLD),
            stylize(divider, COLOR_ACCENT),
        ]
    )


def format_table(rows):
    columns = ["Instance Name", "Machine Type", "Zone", "CPU %"]
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            widths[col] = max(widths[col], len(str(row.get(col, ""))))

    def line_for(row_dict):
        return " | ".join(str(row_dict.get(col, "")).ljust(widths[col]) for col in columns)

    divider = "-+-".join("-" * widths[col] for col in columns)
    header = line_for({col: col for col in columns})
    lines = [
        stylize(header, COLOR_ACCENT, COLOR_BOLD),
        stylize(divider, COLOR_ACCENT),
    ]
    lines.extend(line_for(row) for row in rows)
    return "\n".join(lines)


def format_cpu_value(cpu):
    if cpu is None:
        return "N/A (No Data)"
    return f"{cpu}%"


def load_env_from_file(filename=".env"):
    """Load KEY=VALUE lines from a .env file if present."""
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


def ensure_credentials():
    """Ensure Google ADC is available, otherwise fall back to local gcp-key.json."""
    adc_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if adc_path and os.path.isfile(adc_path):
        return adc_path

    local_key_path = BASE_DIR / "gcp-key.json"
    if local_key_path.is_file():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(local_key_path)
        return str(local_key_path)

    raise FileNotFoundError(
        "Credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or place gcp-key.json next to collector.py."
    )


def get_instances(project_id):
    """Fetch instances from every zone with error handling."""
    try:
        client = compute_v1.InstancesClient()
        request = compute_v1.AggregatedListInstancesRequest(project=project_id)

        instances = []
        for zone, response in client.aggregated_list(request=request):
            if response.instances:
                for instance in response.instances:
                    instances.append(
                        {
                            "name": instance.name,
                            "zone": zone.split("/")[-1],
                            "id": str(instance.id),  # Keep ID as string for API filters
                            "machine_type": instance.machine_type.split("/")[-1],
                            "status": instance.status,
                            "labels": dict(instance.labels),
                            "creation_timestamp": instance.creation_timestamp,
                        }
                    )
        return instances
    except (
        api_exceptions.GoogleAPICallError,
        auth_exceptions.GoogleAuthError,
        requests_exceptions.RequestException,
    ) as e:
        print(f"Error fetching instances: {e}")
        return []


def get_cpu_utilization(project_id, instance_id):
    """Average CPU utilization over the last hour."""
    cpu_average = get_metric_average(
        project_id,
        "compute.googleapis.com/instance/cpu/utilization",
        instance_id,
    )
    if cpu_average is None:
        return None
    return round(cpu_average * 100, 2)


def parse_instance_age_hours(creation_timestamp):
    if not creation_timestamp:
        return None

    normalized = creation_timestamp.replace("Z", "+00:00")
    try:
        created_at = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)
    return round(age.total_seconds() / 3600, 2)


def write_json_file(filename, payload):
    OUTPUTS_DIR.mkdir(exist_ok=True)
    output_path = OUTPUTS_DIR / filename
    with open(output_path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=4)
    return str(output_path)


if __name__ == "__main__":
    env_loaded_from = load_env_from_file()
    if env_loaded_from:
        print(f"Loaded environment variables from: {env_loaded_from}")

    try:
        creds_path = ensure_credentials()
        print(f"Using credentials from: {creds_path}")
    except FileNotFoundError as err:
        print(err)
        raise SystemExit(1)

    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "your-project-id")

    vms = get_instances(PROJECT_ID)
    print(render_banner(f"GCP VM Metrics · {PROJECT_ID}"))
    collected_metrics = []
    display_rows = []

    for vm in vms:
        cpu = get_cpu_utilization(PROJECT_ID, vm["id"])
        display_rows.append(
            {
                "Instance Name": vm["name"],
                "Machine Type": vm["machine_type"],
                "Zone": vm["zone"],
                "CPU %": format_cpu_value(cpu),
            }
        )

        collected_metrics.append(
            VMMetric(
                instance_name=vm["name"],
                machine_type=vm["machine_type"],
                zone=vm["zone"],
                instance_id=vm["id"],
                status=vm["status"],
                labels=vm["labels"],
                creation_timestamp=vm["creation_timestamp"],
                cpu_utilization_avg=cpu,
                memory_utilization_avg=get_metric_average(
                    PROJECT_ID,
                    "agent.googleapis.com/memory/percent_used",
                    vm["id"],
                    extra_filters=['metric.labels.state="used"'],
                ),
                disk_read_bytes_1h=get_metric_sum(
                    PROJECT_ID,
                    "compute.googleapis.com/instance/disk/read_bytes_count",
                    vm["id"],
                ),
                disk_write_bytes_1h=get_metric_sum(
                    PROJECT_ID,
                    "compute.googleapis.com/instance/disk/write_bytes_count",
                    vm["id"],
                ),
                network_in_bytes_1h=get_metric_sum(
                    PROJECT_ID,
                    "compute.googleapis.com/instance/network/received_bytes_count",
                    vm["id"],
                ),
                network_out_bytes_1h=get_metric_sum(
                    PROJECT_ID,
                    "compute.googleapis.com/instance/network/sent_bytes_count",
                    vm["id"],
                ),
                instance_age_hours=parse_instance_age_hours(vm["creation_timestamp"]),
                uptime_total_seconds=get_metric_latest(
                    PROJECT_ID,
                    "compute.googleapis.com/instance/uptime_total",
                    vm["id"],
                    window_seconds=7 * 24 * 3600,
                ),
                estimated_hourly_cost=estimate_hourly_cost(vm["machine_type"], vm["zone"]),
                estimated_monthly_cost=estimate_monthly_cost(vm["machine_type"], vm["zone"]),
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    if display_rows:
        print(format_table(display_rows))
    else:
        print(stylize("No Compute Engine instances found or accessible.", COLOR_WARN))

    raw_metrics_payload = [metric.to_dict() for metric in collected_metrics]
    run_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    recommendations_payload = []
    for recommendation in build_recommendations(collected_metrics):
        recommendation_row = recommendation.to_dict()
        recommendation_row["run_timestamp"] = run_timestamp
        recommendations_payload.append(recommendation_row)
    metrics_path = write_json_file("metrics.json", raw_metrics_payload)
    raw_metrics_path = write_json_file("raw_metrics.json", raw_metrics_payload)
    recommendations_path = write_json_file("recommendations.json", recommendations_payload)

    bq_dataset = os.getenv("BIGQUERY_DATASET")
    bq_export = None
    if bq_dataset:
        bq_export = export_to_bigquery(
            PROJECT_ID,
            bq_dataset,
            raw_metrics_payload,
            recommendations_payload,
        )

    summary = (
        f"Records saved: {len(raw_metrics_payload)} -> {os.path.basename(metrics_path)}, "
        f"{os.path.basename(raw_metrics_path)} | "
        f"Recommendations: {len(recommendations_payload)} -> {os.path.basename(recommendations_path)}"
    )
    if bq_export:
        summary += f" | BigQuery: {bq_export['dataset']}"
    style = COLOR_SUCCESS if raw_metrics_payload else COLOR_WARN
    print(stylize(summary, style))

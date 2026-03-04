import json
import os
import shutil
import sys
import time
from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from requests import exceptions as requests_exceptions
from google.cloud import compute_v1
from google.cloud import monitoring_v3

COLOR_ENABLED = sys.stdout.isatty()
COLOR_RESET = "\033[0m"
COLOR_ACCENT = "\033[96m"
COLOR_SUCCESS = "\033[92m"
COLOR_WARN = "\033[93m"
COLOR_BOLD = "\033[1m"


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
    env_path = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.isfile(env_path):
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

    local_key = os.path.join(os.path.dirname(__file__), "gcp-key.json")
    if os.path.isfile(local_key):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = local_key
        return local_key

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
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    now = time.time()
    interval = monitoring_v3.TimeInterval(
        {"end_time": {"seconds": int(now)}, "start_time": {"seconds": int(now - 3600)}}
    )

    try:
        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": f'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.labels.instance_id="{instance_id}"',
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        points = []
        for result in results:
            for point in result.points:
                points.append(point.value.double_value)

        if not points:
            return None  # Distinguish between zero utilization and no data

        avg_cpu = sum(points) / len(points)
        return round(avg_cpu * 100, 2)
    except (
        api_exceptions.GoogleAPICallError,
        auth_exceptions.GoogleAuthError,
        requests_exceptions.RequestException,
    ) as e:
        print(f"Error fetching metrics for {instance_id}: {e}")
        return None


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
    collected_data = []
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

        data_point = {
            "instance_name": vm["name"],
            "machine_type": vm["machine_type"],
            "zone": vm["zone"],
            "cpu_utilization_avg": cpu if cpu is not None else "N/A",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        collected_data.append(data_point)

    if display_rows:
        print(format_table(display_rows))
    else:
        print(stylize("No Compute Engine instances found or accessible.", COLOR_WARN))

    with open("metrics.json", "w") as f:
        json.dump(collected_data, f, indent=4)

    summary = f"Records saved: {len(collected_data)} -> metrics.json"
    style = COLOR_SUCCESS if collected_data else COLOR_WARN
    print(stylize(summary, style))

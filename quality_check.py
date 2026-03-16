import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
METRICS_PATH = OUTPUTS_DIR / "metrics.json"
RECOMMENDATIONS_PATH = OUTPUTS_DIR / "recommendations.json"
REPORT_JSON_PATH = OUTPUTS_DIR / "quality_report.json"
REPORT_MD_PATH = OUTPUTS_DIR / "quality_report.md"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def run_checks(metrics, recommendations):
    checks = []
    running_instances = [metric for metric in metrics if metric.get("status") == "RUNNING"]
    checks.append(
        {
            "name": "metrics_file_not_empty",
            "status": "pass" if metrics else "fail",
            "detail": f"Collected {len(metrics)} VM record(s).",
        }
    )
    checks.append(
        {
            "name": "recommendations_file_present",
            "status": "pass" if recommendations is not None else "fail",
            "detail": f"Collected {len(recommendations)} recommendation record(s).",
        }
    )

    null_cpu_running = [
        metric["instance_name"]
        for metric in running_instances
        if metric.get("cpu_utilization_avg") is None
    ]
    if not running_instances:
        cpu_check_status = "info"
        cpu_check_detail = "No RUNNING instances in the current sample, so CPU completeness check is not applicable."
    elif not null_cpu_running:
        cpu_check_status = "pass"
        cpu_check_detail = "All RUNNING instances have CPU data."
    else:
        cpu_check_status = "warn"
        cpu_check_detail = f"RUNNING instances missing CPU data: {', '.join(null_cpu_running)}"
    checks.append(
        {
            "name": "running_instances_have_cpu",
            "status": cpu_check_status,
            "detail": cpu_check_detail,
        }
    )

    missing_labels = [
        metric["instance_name"]
        for metric in metrics
        if any(label not in (metric.get("labels") or {}) for label in ("env", "owner", "team", "cost-center"))
    ]
    checks.append(
        {
            "name": "ownership_labels_present",
            "status": "pass" if not missing_labels else "warn",
            "detail": (
                "All instances include ownership labels."
                if not missing_labels
                else f"Instances missing one or more ownership labels: {', '.join(missing_labels)}"
            ),
        }
    )

    terminated_with_activity = []
    for metric in metrics:
        if metric.get("status") != "RUNNING":
            io_total = (metric.get("disk_read_bytes_1h") or 0) + (metric.get("disk_write_bytes_1h") or 0)
            net_total = (metric.get("network_in_bytes_1h") or 0) + (metric.get("network_out_bytes_1h") or 0)
            if io_total > 0 or net_total > 0:
                terminated_with_activity.append(metric["instance_name"])
    checks.append(
        {
            "name": "stopped_instances_with_recent_activity",
            "status": "pass" if not terminated_with_activity else "warn",
            "detail": (
                "No stopped instances show recent activity."
                if not terminated_with_activity
                else "Stopped instances with recent lookback activity: "
                + ", ".join(terminated_with_activity)
            ),
        }
    )

    high_null_fields = {}
    tracked_fields = [
        "cpu_utilization_avg",
        "memory_utilization_avg",
        "disk_read_bytes_1h",
        "disk_write_bytes_1h",
        "network_in_bytes_1h",
        "network_out_bytes_1h",
        "uptime_total_seconds",
    ]
    for field in tracked_fields:
        null_count = sum(1 for metric in metrics if metric.get(field) is None)
        if metrics and null_count / len(metrics) >= 0.5:
            high_null_fields[field] = null_count

    checks.append(
        {
            "name": "null_heavy_fields",
            "status": "pass" if not high_null_fields else "warn",
            "detail": (
                "No tracked metric fields are null-heavy."
                if not high_null_fields
                else "Fields with >=50% nulls: "
                + ", ".join(f"{field} ({count})" for field, count in high_null_fields.items())
            ),
        }
    )

    return checks


def summarize_checks(checks):
    summary = {"pass": 0, "warn": 0, "fail": 0, "info": 0}
    for check in checks:
        summary[check["status"]] += 1
    return summary


def write_outputs(payload):
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=4)

    lines = [
        "# Data Quality Report",
        "",
        f"Pass: {payload['summary']['pass']}",
        f"Info: {payload['summary']['info']}",
        f"Warn: {payload['summary']['warn']}",
        f"Fail: {payload['summary']['fail']}",
        "",
        "## Checks",
    ]
    for check in payload["checks"]:
        lines.append(f"- [{check['status'].upper()}] {check['name']}: {check['detail']}")

    with open(REPORT_MD_PATH, "w", encoding="utf-8") as file_obj:
        file_obj.write("\n".join(lines) + "\n")


def main():
    metrics = load_json(METRICS_PATH)
    recommendations = load_json(RECOMMENDATIONS_PATH)
    checks = run_checks(metrics, recommendations)
    payload = {
        "summary": summarize_checks(checks),
        "checks": checks,
    }
    write_outputs(payload)
    print(f"Quality report written: {REPORT_JSON_PATH.name}, {REPORT_MD_PATH.name}")


if __name__ == "__main__":
    main()

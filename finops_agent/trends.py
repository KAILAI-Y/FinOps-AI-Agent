import os
from pathlib import Path

from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import bigquery
from requests import exceptions as requests_exceptions


LOW_CPU_THRESHOLD = 10.0
IDLE_EXPENSIVE_COST_THRESHOLD = 50.0
IDLE_EXPENSIVE_LOW_UTIL_DAYS_THRESHOLD = 3
BASE_DIR = Path(__file__).resolve().parent.parent


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


def fetch_historical_trends(project_id, dataset_name):
    if not dataset_name:
        return {}

    try:
        client = bigquery.Client(project=project_id)
        table_id = f"{project_id}.{dataset_name}.raw_metrics"
        query = f"""
        SELECT
          instance_id,
          ANY_VALUE(instance_name) AS instance_name,
          ROUND(AVG(cpu_utilization_avg), 2) AS seven_day_avg_cpu,
          COUNT(DISTINCT CASE
            WHEN cpu_utilization_avg IS NOT NULL AND cpu_utilization_avg <= @low_cpu_threshold
            THEN DATE(timestamp)
          END) AS seven_day_low_utilization_days,
          ROUND(AVG(estimated_monthly_cost), 2) AS seven_day_avg_monthly_cost
        FROM `{table_id}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        GROUP BY instance_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("low_cpu_threshold", "FLOAT64", LOW_CPU_THRESHOLD),
            ]
        )
        rows = client.query(query, job_config=job_config).result()
        trends = {}
        for row in rows:
            seven_day_avg_cpu = row.seven_day_avg_cpu
            seven_day_low_utilization_days = int(row.seven_day_low_utilization_days or 0)
            avg_monthly_cost = row.seven_day_avg_monthly_cost
            trends[row.instance_id] = {
                "seven_day_avg_cpu": float(seven_day_avg_cpu) if seven_day_avg_cpu is not None else None,
                "seven_day_low_utilization_days": seven_day_low_utilization_days,
                "idle_but_expensive_flag": bool(
                    avg_monthly_cost is not None
                    and avg_monthly_cost >= IDLE_EXPENSIVE_COST_THRESHOLD
                    and seven_day_low_utilization_days >= IDLE_EXPENSIVE_LOW_UTIL_DAYS_THRESHOLD
                ),
            }
        return trends
    except (
        api_exceptions.GoogleAPICallError,
        auth_exceptions.GoogleAuthError,
        requests_exceptions.RequestException,
    ) as exc:
        print(f"Historical trend query failed: {exc}")
        return {}


def apply_historical_trends(metrics, trends):
    for metric in metrics:
        trend = trends.get(metric.instance_id)
        if not trend:
            continue
        metric.seven_day_avg_cpu = trend["seven_day_avg_cpu"]
        metric.seven_day_low_utilization_days = trend["seven_day_low_utilization_days"]
        metric.idle_but_expensive_flag = trend["idle_but_expensive_flag"]
    return metrics


def build_trend_analysis(metrics):
    instances = []
    for metric in metrics:
        if metric.seven_day_avg_cpu is None and metric.seven_day_low_utilization_days is None:
            continue
        instances.append(
            {
                "instance_name": metric.instance_name,
                "instance_id": metric.instance_id,
                "status": metric.status,
                "seven_day_avg_cpu": metric.seven_day_avg_cpu,
                "seven_day_low_utilization_days": metric.seven_day_low_utilization_days,
                "idle_but_expensive_flag": metric.idle_but_expensive_flag,
                "estimated_monthly_cost": metric.estimated_monthly_cost,
            }
        )

    instances.sort(
        key=lambda item: (
            not item["idle_but_expensive_flag"],
            -(item["seven_day_low_utilization_days"] or 0),
            item["seven_day_avg_cpu"] if item["seven_day_avg_cpu"] is not None else float("inf"),
        )
    )

    return {
        "summary": {
            "trend_ready_instances": len(instances),
            "persistent_low_utilization_instances": sum(
                1 for item in instances if (item["seven_day_low_utilization_days"] or 0) >= 3
            ),
            "idle_but_expensive_instances": sum(
                1 for item in instances if item["idle_but_expensive_flag"]
            ),
        },
        "instances": instances,
    }

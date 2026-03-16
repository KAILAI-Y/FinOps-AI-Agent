import json

from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import bigquery
from requests import exceptions as requests_exceptions


RAW_METRICS_SCHEMA = [
    bigquery.SchemaField("instance_name", "STRING"),
    bigquery.SchemaField("machine_type", "STRING"),
    bigquery.SchemaField("zone", "STRING"),
    bigquery.SchemaField("instance_id", "STRING"),
    bigquery.SchemaField("status", "STRING"),
    bigquery.SchemaField("labels", "STRING"),
    bigquery.SchemaField("creation_timestamp", "TIMESTAMP"),
    bigquery.SchemaField("cpu_utilization_avg", "FLOAT"),
    bigquery.SchemaField("memory_utilization_avg", "FLOAT"),
    bigquery.SchemaField("disk_read_bytes_1h", "FLOAT"),
    bigquery.SchemaField("disk_write_bytes_1h", "FLOAT"),
    bigquery.SchemaField("network_in_bytes_1h", "FLOAT"),
    bigquery.SchemaField("network_out_bytes_1h", "FLOAT"),
    bigquery.SchemaField("instance_age_hours", "FLOAT"),
    bigquery.SchemaField("uptime_total_seconds", "FLOAT"),
    bigquery.SchemaField("estimated_hourly_cost", "FLOAT"),
    bigquery.SchemaField("estimated_monthly_cost", "FLOAT"),
    bigquery.SchemaField("timestamp", "TIMESTAMP"),
]

RECOMMENDATIONS_SCHEMA = [
    bigquery.SchemaField("instance_name", "STRING"),
    bigquery.SchemaField("category", "STRING"),
    bigquery.SchemaField("severity", "STRING"),
    bigquery.SchemaField("summary", "STRING"),
    bigquery.SchemaField("rationale", "STRING"),
    bigquery.SchemaField("suggested_action", "STRING"),
    bigquery.SchemaField("estimated_savings_hint", "STRING"),
    bigquery.SchemaField("run_timestamp", "TIMESTAMP"),
]


def export_to_bigquery(project_id, dataset_name, raw_metrics_rows, recommendation_rows):
    try:
        client = bigquery.Client(project=project_id)
        dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_name}")
        client.create_dataset(dataset_ref, exists_ok=True)

        raw_table_id = f"{project_id}.{dataset_name}.raw_metrics"
        recommendations_table_id = f"{project_id}.{dataset_name}.recommendations"
        prepared_raw_rows = [_prepare_raw_metrics_row(row) for row in raw_metrics_rows]

        _ensure_table(client, raw_table_id, RAW_METRICS_SCHEMA)
        _ensure_table(client, recommendations_table_id, RECOMMENDATIONS_SCHEMA)
        _insert_rows(client, raw_table_id, prepared_raw_rows)
        _insert_rows(client, recommendations_table_id, recommendation_rows)
        return {
            "dataset": f"{project_id}.{dataset_name}",
            "raw_table": raw_table_id,
            "recommendations_table": recommendations_table_id,
        }
    except (
        api_exceptions.GoogleAPICallError,
        auth_exceptions.GoogleAuthError,
        requests_exceptions.RequestException,
    ) as exc:
        print(f"BigQuery export failed: {exc}")
        return None


def _ensure_table(client, table_id, schema):
    table = bigquery.Table(table_id, schema=schema)
    client.create_table(table, exists_ok=True)


def _prepare_raw_metrics_row(row):
    prepared = dict(row)
    prepared["labels"] = json.dumps(prepared.get("labels", {}), sort_keys=True)
    return prepared


def _insert_rows(client, table_id, rows):
    if not rows:
        return
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"Failed to insert rows into {table_id}: {errors}")

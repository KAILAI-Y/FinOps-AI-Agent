import time

from google.api_core import exceptions as api_exceptions
from google.auth import exceptions as auth_exceptions
from google.cloud import monitoring_v3
from requests import exceptions as requests_exceptions


def build_time_interval(window_seconds):
    now = time.time()
    return monitoring_v3.TimeInterval(
        {"end_time": {"seconds": int(now)}, "start_time": {"seconds": int(now - window_seconds)}}
    )


def list_time_series(project_id, metric_type, instance_id, window_seconds=3600, extra_filters=None):
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    filters = [
        f'metric.type="{metric_type}"',
        f'resource.labels.instance_id="{instance_id}"',
    ]
    if extra_filters:
        filters.extend(extra_filters)

    try:
        return client.list_time_series(
            request={
                "name": project_name,
                "filter": " AND ".join(filters),
                "interval": build_time_interval(window_seconds),
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )
    except (
        api_exceptions.GoogleAPICallError,
        auth_exceptions.GoogleAuthError,
        requests_exceptions.RequestException,
    ) as exc:
        print(f"Error fetching {metric_type} for {instance_id}: {exc}")
        return []


def _point_value(point):
    value = point.value
    protobuf_value = getattr(value, "_pb", value)
    kind = protobuf_value.WhichOneof("value")
    if kind == "double_value":
        return value.double_value
    if kind == "int64_value":
        return value.int64_value
    return None


def get_metric_average(project_id, metric_type, instance_id, window_seconds=3600, extra_filters=None):
    points = []
    for result in list_time_series(project_id, metric_type, instance_id, window_seconds, extra_filters):
        for point in result.points:
            point_value = _point_value(point)
            if point_value is not None:
                points.append(point_value)

    if not points:
        return None
    return round(sum(points) / len(points), 2)


def get_metric_sum(project_id, metric_type, instance_id, window_seconds=3600, extra_filters=None):
    total = 0.0
    found = False
    for result in list_time_series(project_id, metric_type, instance_id, window_seconds, extra_filters):
        for point in result.points:
            point_value = _point_value(point)
            if point_value is not None:
                total += point_value
                found = True

    if not found:
        return None
    return round(total, 2)


def get_metric_latest(project_id, metric_type, instance_id, window_seconds=3600, extra_filters=None):
    latest_value = None
    latest_seconds = None
    for result in list_time_series(project_id, metric_type, instance_id, window_seconds, extra_filters):
        for point in result.points:
            point_value = _point_value(point)
            if point_value is None:
                continue
            end_time = point.interval.end_time
            if not end_time:
                seconds = 0
            elif hasattr(end_time, "timestamp"):
                seconds = end_time.timestamp()
            else:
                seconds = end_time.seconds
            if latest_seconds is None or seconds > latest_seconds:
                latest_seconds = seconds
                latest_value = point_value

    if latest_value is None:
        return None
    return round(latest_value, 2)

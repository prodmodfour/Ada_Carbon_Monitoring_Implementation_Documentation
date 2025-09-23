import typing

def to_rfc3339(date: datetime):
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    else:
        date = date.astimezone(timezone.utc)
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')


def cpu_seconds_total(prometheus_client: PrometheusAPIClient, timestamp: datetime, cloud_project_name: str, step = '1h'):
    query = f'increase(node_cpu_seconds_total{{cloud_project_name="{cloud_project_name}"}}[{step}])'

    parameters = {
        "query": query,
        "start": to_rfc3339(timestamp),
        "end": to_rfc3339(timestamp),
        "step": step
    }

    response = prometheus_client.query(parameters)

    return response

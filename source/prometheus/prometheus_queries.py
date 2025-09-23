
def cpu_seconds_total(prometheus_client, timestamp, cloud_project_name, step = '1h'):
    query = f'increase(node_cpu_seconds_total{{cloud_project_name="{cloud_project_name}"}}[{step}])'

    parameters = {
        "query": query,
        "start": to_rfc3339(timestamp),
        "end": to_rfc3339(timestamp),
        "step": step
    }

    response = prometheus_client.query(parameters)

    return response

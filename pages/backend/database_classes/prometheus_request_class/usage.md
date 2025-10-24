---
title: Usage
parent: Prometheus Request Class
nav_order: 2
---

# Usage

## Basic: per-series increase over 5 minutes

```python
client = PrometheusAPIClient(
    prometheus_url="https://host-172-16-100-248.nubes.stfc.ac.uk/",
    api_endpoint="api/v1/query_range",
    timeout=120,
)

params = {
    # increase over a 5-minute lookback, evaluated every 30s
    "query": 'increase(http_requests_total{job="api"}[5m])',
    "start": "2025-10-24T08:00:00Z",
    "end":   "2025-10-24T10:00:00Z",
    "step":  "30s",
}

data = client.query(params)
```

## Aggregate: total increase by status code over 15 minutes

```python
params = {
    "query": 'sum by (status) (increase(http_requests_total{job="api"}[15m]))',
    "start": "2025-10-24T08:00:00Z",
    "end":   "2025-10-24T12:00:00Z",
    "step":  "5m",
}

data = client.query(params)
```

## RFC 3339 with timezone offset (BST example, +01:00)

```python
params = {
    "query": 'sum by (handler) (increase(http_requests_total{job="api"}[1h]))',
    "start": "2025-10-24T09:00:00+01:00",  # same instant as 08:00:00Z
    "end":   "2025-10-24T13:00:00+01:00",
    "step":  "10m",
}

data = client.query(params)
```

## Filtering: only 5xx responses, per-route

```python
params = {
    "query": 'sum by (route) (increase(http_requests_total{job="api",status=~"5.."}[30m]))',
    "start": "2025-10-24T08:00:00Z",
    "end":   "2025-10-24T11:00:00Z",
    "step":  "1m",
}

data = client.query(params)
```

Tip: `start`/`end` **must** be RFC 3339 strings (e.g., `YYYY-MM-DDTHH:MM:SSZ` or with an offset like `+01:00`). `step` is a Prometheus duration (`30s`, `5m`, `1h`).

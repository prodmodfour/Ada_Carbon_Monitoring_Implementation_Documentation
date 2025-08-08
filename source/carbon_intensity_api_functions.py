from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, Optional, Tuple, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.carbonintensity.org.uk"
ISO_MIN = "%Y-%m-%dT%H:%MZ"

# Session Helpers
def _make_session(timeout: float = 10.0, total_retries: int = 3) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=total_retries,
        connect=total_retries,
        read=total_retries,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.request = _with_timeout(s.request, timeout)  # type: ignore
    return s

def _with_timeout(func, timeout: float):
    def wrapper(method, url, **kwargs):
        kwargs.setdefault("timeout", timeout)
        return func(method, url, **kwargs)
    return wrapper

SESSION = _make_session()

# Data Helpers
Dateish = Union[str, dt.datetime, dt.date]

def _to_iso_min_z(t):
    """Convert various date-like inputs to ISO minute precision with 'Z' (UTC)."""
    if isinstance(t, str):
        return t  # assume caller provided ISO-ish; the API is lenient
    if isinstance(t, dt.date) and not isinstance(t, dt.datetime):
        # interpret date as midnight UTC
        t = dt.datetime(t.year, t.month, t.day, tzinfo=dt.UTC)
    # If naive, assume UTC; otherwise convert to UTC
    if t.tzinfo is None:
        t = t.replace(tzinfo=dt.UTC)
    else:
        t = t.astimezone(dt.UTC)
    t = t.replace(second=0, microsecond=0)
    return t.strftime("%Y-%m-%dT%H:%MZ")

def _get_json(path: str, params: Optional[Dict[str, Any]] = None, *, session: requests.Session = SESSION) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    r = session.get(url, params=params)
    r.raise_for_status()
    return r.json()

def _get_data(path: str, params: Optional[Dict[str, Any]] = None, *, session: requests.Session = SESSION):
    try:
        payload = _get_json(path, params=params, session=session)
        return payload.get("data", payload)  # some endpoints return {"data": ...}
    except requests.RequestException as e:
        # Keep this compact but informative
        text = getattr(e.response, "text", "")
        raise RuntimeError(f"Carbon Intensity API error for {path}: {e} | {text}") from e

# National Intensity
def get_current_intensity(*, session: requests.Session = SESSION):
    """Current national carbon intensity."""
    return _get_data("/intensity", session=session)

def get_intensity_range(start: Dateish, end: Dateish, *, session: requests.Session = SESSION):
    """Half-hourly national intensity for a time range [start, end]."""
    s = _to_iso_min_z(start)
    e = _to_iso_min_z(end)
    return _get_data(f"/intensity/{s}/{e}", session=session)

def get_intensity_on_date(date: Dateish, *, session: requests.Session = SESSION):
    """Half-hourly national intensity for a given calendar date (UTC)."""
    if isinstance(date, str):
        day = date
    else:
        if isinstance(date, dt.datetime):
            date = date.date()
        day = date.strftime("%Y-%m-%d")
    return _get_data(f"/intensity/date/{day}", session=session)

def get_forecast_fw48h(start: Optional[Dateish] = None, *, session: requests.Session = SESSION):
    """
    Forward-looking forecast out to ~48h from 'start'.
    If start is None, uses current hour (UTC) rounded to minute precision.
    """
    if start is None:
        now = dt.datetime.now(dt.UTC).replace(minute=0, second=0, microsecond=0)

        start = now
    s = _to_iso_min_z(start)
    return _get_data(f"/intensity/{s}/fw48h", session=session)

def get_intensity_stats(start: Dateish, end: Dateish, group_by: Optional[str] = None, *, session: requests.Session = SESSION):
    """
    Summary stats for a period. Optional group_by: 'day', 'month', or 'year'.
    """
    s = _to_iso_min_z(start)
    e = _to_iso_min_z(end)
    params = {"groupBy": group_by} if group_by else None
    return _get_data(f"/intensity/stats/{s}/{e}", params=params, session=session)

def get_factors(*, session: requests.Session = SESSION):
    """Emissions factors (gCO2/kWh) for fuels."""
    return _get_data("/intensity/factors", session=session)

# Generation mix (national)
def get_generation_mix_current(*, session: requests.Session = SESSION):
    """Current national generation mix."""
    return _get_data("/generation", session=session)

def get_generation_mix_range(start: Dateish, end: Dateish, *, session: requests.Session = SESSION):
    """Generation mix time series for a range."""
    s = _to_iso_min_z(start)
    e = _to_iso_min_z(end)
    return _get_data(f"/generation/{s}/{e}", session=session)

# Regional intensity
# Notes:
# - The API provides regional snapshots and time-series.
# - Endpoints commonly used (kept here as thin wrappers):
#     /regional
#     /regional/{regionid}
#     /regional/intensity/{start}/{end}
#     /regional/{regionid}/intensity/{start}/{end}
# - Region IDs correspond to DNO/GSP regions; use get_regional() to discover them.

def get_regional_snapshot(*, session: requests.Session = SESSION):
    """Current snapshot for all regions (includes region IDs & names)."""
    return _get_data("/regional", session=session)

def get_regional_snapshot_by_id(region_id: Union[int, str], *, session: requests.Session = SESSION):
    """Current snapshot for a single region by ID."""
    return _get_data(f"/regional/{region_id}", session=session)

def get_regional_intensity_range(start: Dateish, end: Dateish, region_id: Optional[Union[int, str]] = None, *, session: requests.Session = SESSION):
    """
    Regional half-hourly intensity time series for [start, end].
    If region_id is None, returns all regions; else returns specified region only.
    """
    s = _to_iso_min_z(start)
    e = _to_iso_min_z(end)
    if region_id is None:
        return _get_data(f"/regional/intensity/{s}/{e}", session=session)
    return _get_data(f"/regional/{region_id}/intensity/{s}/{e}", session=session)

# Convenience
def half_hours(n: int, *, start: Optional[dt.datetime] = None) -> Iterable[Tuple[dt.datetime, dt.datetime]]:
    """
    Yield n consecutive half-hour windows [t, t+30m), starting from the next
    half-hour boundary after 'start' (UTC).
    """
    if start is None:
        start = dt.datetime.utcnow().replace(second=0, microsecond=0)
    if start.tzinfo is None:
        start = start.replace(tzinfo=dt.timezone.utc)
    # snap to next :00 or :30
    minute = 30 if start.minute < 30 else 0
    hour = start.hour + (1 if minute == 0 else 0)
    t = start.replace(minute=minute, second=0, microsecond=0)
    if minute == 0:
        t = t.replace(hour=hour)
    for _ in range(n):
        yield (t, t + dt.timedelta(minutes=30))
        t = t + dt.timedelta(minutes=30)

# Example CLI
if __name__ == "__main__":
    # quick smoke tests
    cur = get_current_intensity()
    print(f"current intensity entries: {len(cur)}")

    now = dt.datetime.now(dt.UTC).replace(minute=0, second=0, microsecond=0)

    fw = get_forecast_fw48h(now)
    print(f"fw48h entries: {len(fw)}")

    # one day range
    start = now
    end = now + dt.timedelta(hours=1)
    r = get_intensity_range(start, end)
    print(f"range entries: {len(r)}")

    mix = get_generation_mix_current()
    print(f"generation mix entries: {len(mix)}")

    regional = get_regional_snapshot()
    print(f"regional snapshot regions: {len(regional)}")

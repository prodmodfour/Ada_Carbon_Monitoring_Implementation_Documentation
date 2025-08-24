# main/views.py — refactored (dev-only)

from __future__ import annotations

import hashlib
import json
import math
import random
import time
import uuid
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
from django.conf import settings
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.utils import timezone as dj_tz
from django.utils.timezone import now as tz_now

from .models import ProjectEnergy

# ========= DEBUG PRINT HELPER =========
def _dbg(enabled: bool, *args) -> None:
    """Console prints only when enabled=True."""
    if enabled:
        print("[ENERGY DEBUG]", *args)
# =====================================

# -----------------------------
# Constants 
# -----------------------------


DEFAULT_TDP_SPEC = {
    "cpu_count": 12,    # logical or physical; up to you
    "cpu_tdp_w": 12,    # per-core watts under typical load (not peak)
    "gpu_count": 0,
    "gpu_tdp_w": 250,   # per-GPU watts
    "ram_w": 20,        # system/ram etc
    "other_w": 30,      # misc platform overhead
}

DEFAULT_EMBODIED = {
    "cpu_kg": 30,     # per CPU package
    "gpu_kg": 320,    # per accelerator
    "system_kg": 100, # motherboard/chassis/psu share
}

DEFAULT_CI_G_PER_KWH = 220         # location-based intensity (g/kWh)
DEFAULT_LIFETIME_HOURS = 3 * 365 * 8  # 3 years @ 8h/day (simplified)

PROJECT_TO_LABELVAL = {
    "clf": "CDAaaS",
    "isis": "IDAaaS",
    "diamond": "DDAaaS",
}

ISIS_INSTRUMENTS = [
    'ALF','ARGUS','CHRONUS','CRISP','EMU','ENGINX','GEM','HIFI','HRPD','IMAT','INES','INTER',
    'IRIS','LARMOR','LET','LOQ','MAPS','MARI','MERLIN','MUSR','NEUTRONICS','NIMROD','NMIDG',
    'OFFSPEC','OSIRIS','PEARL','POLARIS','POLREF','SANDALS','SANS2D','SURF','SXD','TOSCA',
    'VESUVIO','WISH','ZOOM'
]
CLF_INSTRUMENTS = ['ARTEMIS', 'EPAC', 'GEMINI', 'OCTOPUS', 'ULTRA', 'VULCAN']

# -----------------------------
# Small helpers
# -----------------------------
def _spec_hash(spec: dict) -> str:
    payload = (
        f"cpu_count={spec.get('cpu_count')};"
        f"cpu_tdp_w={spec.get('cpu_tdp_w')};"
        f"gpu_count={spec.get('gpu_count')};"
        f"gpu_tdp_w={spec.get('gpu_tdp_w')};"
        f"ram_w={spec.get('ram_w')};"
        f"other_w={spec.get('other_w')}"
    ).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()

def _cache_ttl_seconds(range_key: str) -> int:
    return {"day": 3600, "month": 24 * 3600, "year": 24 * 3600}[range_key]

def _bin_meta(range_key: str) -> Tuple[int, int, int]:
    end = int(time.time())
    if range_key == "day":
        start, step_s = end - 24 * 3600, 3600
    elif range_key == "month":
        start, step_s = end - 30 * 86400, 86400
    elif range_key == "year":
        start, step_s = end - 365 * 86400, 86400
    else:
        raise ValueError("range must be day|month|year")
    return start, end, step_s

def _seeded_rng(seed: str = "project") -> random.Random:
    return random.Random(seed)

def _util_profile_day(hour: int) -> float:
    """Diurnal utilization curve 0..1."""
    base = 0.25 + 0.45 * math.sin((hour - 8) * math.pi / 12)  # peaks around mid-day
    return max(0.05, min(0.95, base))

def _make_series(range_key: str, spec: dict) -> Tuple[List[str], List[float]]:
    """
    Build labels + kWh per bin for:
      - day: 24 hourly bins
      - month: 30 daily bins (dummy month)
      - year: 12 monthly bins
    """
    rng = _seeded_rng("project-usage")
    labels: List[str] = []
    kwh: List[float] = []

    full_watts = (
        spec["cpu_count"] * spec["cpu_tdp_w"]
        + spec["gpu_count"] * spec["gpu_tdp_w"]
        + spec["ram_w"]
        + spec["other_w"]
    )

    if range_key == "day":
        for h in range(24):
            util = _util_profile_day(h) + rng.uniform(-0.05, 0.05)
            util = max(0.05, min(0.95, util))
            watts = full_watts * util
            kwh.append(round(watts / 1000 * 1.0, 3))
            labels.append(f"{h:02d}:00")
    elif range_key == "month":
        for d in range(1, 31):
            weekday = (d % 7) not in (6, 0)
            util = (0.55 if weekday else 0.35) + rng.uniform(-0.08, 0.08)
            util = max(0.05, min(0.95, util))
            hours = 8 if weekday else 4
            kwh.append(round(full_watts / 1000 * hours, 3))
            labels.append(f"D{d}")
    elif range_key == "year":
        for m in range(1, 13):
            season = 0.6 if m in (2, 3, 10, 11) else 0.5
            util = season + rng.uniform(-0.07, 0.07)
            util = max(0.05, min(0.95, util))
            hours = 8 * 22
            kwh.append(round(full_watts / 1000 * hours * util, 2))
            labels.append(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1])
    else:
        return [], []

    return labels, kwh

def _stable_specs_for(instrument_name: str) -> dict:
    r = random.Random(instrument_name.lower())
    cpus = r.choice([4, 8, 12, 16, 24, 32, 48, 64])
    ram  = r.choice([16, 24, 32, 48, 64, 96, 128, 192, 256])  # GB
    gpus = r.choice([0, 1, 1, 2, 2, 4])  # weight toward 1–2 GPUs
    return {"cpus": cpus, "ram": ram, "gpus": gpus}

def _instrument_hourly_figures(inst_name: str, ci_gpkwh: float = DEFAULT_CI_G_PER_KWH) -> Tuple[float, float]:
    """
    Dummy average electricity/carbon usage per hour for an instrument.
    Uses your deterministic hardware spec + a simple average utilization.
    """
    spec = DEFAULT_TDP_SPEC.copy()
    hw = _stable_specs_for(inst_name)
    spec["cpu_count"] = int(hw.get("cpus", spec["cpu_count"]))
    spec["gpu_count"] = int(hw.get("gpus", spec["gpu_count"]))

    full_watts = (
        spec["cpu_count"] * spec["cpu_tdp_w"]
        + spec["gpu_count"] * spec["gpu_tdp_w"]
        + spec["ram_w"]
        + spec["other_w"]
    )

    avg_util = 0.60
    kwh_per_hour = (full_watts * avg_util) / 1000.0
    kg_per_hour  = kwh_per_hour * (ci_gpkwh / 1000.0)
    return round(kwh_per_hour, 2), round(kg_per_hour, 2)

# -----------------------------
# Workspace session helpers (single definitions)
# -----------------------------
def _ws_key(source: str) -> str:
    return f"workspaces::{source.lower()}"

def _get_workspaces(request: HttpRequest, source: str) -> List[dict]:
    return request.session.get(_ws_key(source), [])

def _save_workspaces(request: HttpRequest, source: str, items: List[dict]) -> None:
    request.session[_ws_key(source)] = items
    request.session.modified = True

def _ensure_workspace_ids(request: HttpRequest, source: str) -> List[dict]:
    """Upgrade any pre-existing session items to include a UUID id."""
    items = _get_workspaces(request, source)
    changed = False
    for ws in items:
        if "id" not in ws:
            ws["id"] = str(uuid.uuid4())
            changed = True
    if changed:
        _save_workspaces(request, source, items)
    return items

def _get_workspace(request: HttpRequest, source: str, ws_id: str) -> Optional[dict]:
    for ws in _ensure_workspace_ids(request, source):
        if ws.get("id") == ws_id:
            return ws
    return None

def _delete_workspace(request: HttpRequest, source: str, ws_id: str) -> None:
    items = [w for w in _get_workspaces(request, source) if w.get("id") != ws_id]
    _save_workspaces(request, source, items)

def _add_workspace(request: HttpRequest, source: str, instrument: str) -> None:
    items = _get_workspaces(request, source)
    next_num = len(items) + 1
    now = dj_tz.now()
    wid = str(uuid.uuid4())
    rnd = random.Random(wid)
    host = f"host-10-{rnd.randint(0,255)}-{rnd.randint(0,255)}-{rnd.randint(0,255)}.local"

    items.append({
        "id": wid,
        "title": f"Workspace {next_num}",
        "owner": "Ashraf Hussain",
        "instrument": instrument,
        "hostname": host,
        "created_at": now.isoformat(),
        "last_activity": now.isoformat(),
        "recycle_at": (now + timedelta(days=7)).isoformat(),
        "health": {"overall": "pass", "babylon": "pass", "ceph": "pass"},
    })
    _save_workspaces(request, source, items)

# -----------------------------
# Views (pages)
# -----------------------------
def home(request: HttpRequest) -> HttpResponse:
    """Landing page with cards linking to analysis pages."""
    return render(request, "home.html")

def analysis(request: HttpRequest, source: str) -> HttpResponse:
    items = _ensure_workspace_ids(request, source)
    enriched = [{**ws, **_estimate_ws_metrics(ws)} for ws in items]

    context = {
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source.lower(), f"{source.title()} Data Analysis"),
        "source": source,
        "workspaces": enriched,
    }
    return render(request, "analysis.html", context)

def instruments(request: HttpRequest, source: str) -> HttpResponse:
    source_key = source.lower()
    base_list = ISIS_INSTRUMENTS if source_key == "isis" else CLF_INSTRUMENTS

    enriched = []
    for name in base_list:
        kwh_h, kg_h = _instrument_hourly_figures(name)
        enriched.append({"name": name, "kwh_per_hour": kwh_h, "kg_per_hour": kg_h})

    context = {
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source_key, f"{source.title()} Data Analysis"),
        "instruments": enriched,
        "source": source,
    }
    template_name = "instruments_isis.html" if source_key == "isis" else "instruments_clf.html"
    return render(request, template_name, context)

def instrument_detail(request: HttpRequest, source: str, instrument: str) -> HttpResponse:
    # Only redirect after a real "Create Workspace" POST
    if request.method == "POST" and request.POST.get("create_workspace") == "1":
        _add_workspace(request, source, instrument)
        return redirect("analysis", source=source)

    context = {
        "source": source,
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source.lower(), f"{source.title()} Data Analysis"),
        "instrument_name": instrument,
        "specs": _stable_specs_for(instrument),
    }
    return render(request, "instrument_detail.html", context)

def workspace_detail(request: HttpRequest, source: str, ws_id: str) -> HttpResponse:
    ws = _get_workspace(request, source, ws_id)
    if not ws:
        return redirect("analysis", source=source)

    # Delete action
    if request.method == "POST" and request.POST.get("delete") == "1":
        _delete_workspace(request, source, ws_id)
        return redirect("analysis", source=source)

    # Touch last activity for demo purposes
    ws["last_activity"] = dj_tz.now().isoformat()
    items = _get_workspaces(request, source)
    for i, w in enumerate(items):
        if w.get("id") == ws_id:
            items[i] = ws
            break
    _save_workspaces(request, source, items)

    context = {
        "source": source,
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source.lower(), f"{source.title()} Data Analysis"),
        "ws": ws,
    }
    return render(request, "workspace_detail.html", context)

# -----------------------------
# APIs
# -----------------------------
def ci_proxy(request: HttpRequest) -> HttpResponse:
    """
    Server-side proxy for the GB Carbon Intensity API.
    Accepts GET ?from=<ISO8601 UTC> & to=<ISO8601 UTC>
    """
    frm = request.GET.get("from")
    to = request.GET.get("to")
    if not frm or not to:
        return HttpResponseBadRequest("Query params 'from' and 'to' are required.")

    base = "https://api.carbonintensity.org.uk/intensity"
    safe = ":-TZ"
    url = f"{base}/{urllib.parse.quote(frm, safe=safe)}/{urllib.parse.quote(to, safe=safe)}"

    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read().decode(charset)
            payload = json.loads(data)
            return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)

def project_usage_api(request: HttpRequest) -> HttpResponse:
    """
    Return energy series for the project cards.

    Modes (settings.PROM_DATA_MODE):
      - "db_only": serve cached DB rows only; if not cached -> 503
      - "prom_on_miss" (default): use DB if fresh; otherwise compute and cache.

    Query params:
      - range: day|month|year
      - source: clf|isis|diamond   (others fall back to mock series, no DB)
      - debug: 1|true
      - force_refresh: 1|true      (ignored in db_only mode)
      - Optional overrides:
          cpu_count, cpu_tdp_w, gpu_count, gpu_tdp_w, ram_w, other_w
    """
    mode = getattr(settings, "PROM_DATA_MODE", "prom_on_miss")
    debug = str(request.GET.get("debug", "")).lower() in ("1", "true", "yes", "on")
    range_key = (request.GET.get("range") or "day").lower()
    source = (request.GET.get("source") or "").lower()
    force_refresh = str(request.GET.get("force_refresh", "")).lower() in ("1", "true", "yes", "on")

    _dbg(debug, "REQUEST", {"mode": mode, "range": range_key, "source": source, "qs": dict(request.GET)})

    if range_key not in ("day", "month", "year"):
        return HttpResponseBadRequest("range must be day|month|year")

    # build spec (with optional overrides) + hash
    spec = DEFAULT_TDP_SPEC.copy()
    for key in ("cpu_count", "cpu_tdp_w", "gpu_count", "gpu_tdp_w", "ram_w", "other_w"):
        if key in request.GET:
            try:
                spec[key] = float(request.GET.get(key))
            except Exception:
                pass
    shash = _spec_hash(spec)

    # DB lookup
    ttl = _cache_ttl_seconds(range_key)
    can_cache = source in ("clf", "isis", "diamond")
    row = (
        ProjectEnergy.objects.filter(source=source, range_key=range_key, spec_hash=shash)
        .order_by("-updated_at")
        .first()
        if can_cache
        else None
    )

    if mode == "db_only":
        if row:
            data = {
                "range": range_key,
                "labels": row.labels,
                "kwh": row.kwh,
                "total_kwh": row.total_kwh,
                "spec": spec,
            }
            _dbg(debug, "RESPONSE(DB_ONLY)", {"id": row.id, "labels_len": len(row.labels), "kwh_len": len(row.kwh)})
            return JsonResponse(data)
        msg = (
            "No cached PromQL data for this (source, range, spec). "
            "Warm the cache first, e.g.:\n"
            "  python manage.py refresh_energy_cache --sources clf,isis,diamond --ranges day,month,year"
        )
        _dbg(debug, "DB_ONLY_MISS", msg)
        return JsonResponse({"error": msg}, status=503)

    # Not db_only: use cache if fresh and not force_refresh
    if row and not force_refresh:
        age_s = (tz_now() - row.updated_at).total_seconds()
        _dbg(debug, "CACHE_HIT", {"id": row.id, "age_s": int(age_s), "ttl_s": ttl})
        if age_s < ttl:
            data = {
                "range": range_key,
                "labels": row.labels,
                "kwh": row.kwh,
                "total_kwh": row.total_kwh,
                "spec": spec,
            }
            _dbg(debug, "RESPONSE(DB)", {"labels_len": len(row.labels), "kwh_len": len(row.kwh)})
            return JsonResponse(data)

    # compute (prom -> fallback to mock)
    try:
        if source in PROJECT_TO_LABELVAL:
            labels, kwh = _prometheus_usage_series(source, range_key, spec, debug)
        else:
            _dbg(debug, "FALLBACK_MOCK_SERIES")
            labels, kwh = _make_series(range_key, spec)
    except Exception as e:
        _dbg(debug, "COMPUTE_ERROR", repr(e))
        labels, kwh = _make_series(range_key, spec)

    total_kwh = round(sum(kwh), 3)

    # best-effort cache
    if can_cache:
        try:
            s, e, step_s = _bin_meta(range_key)
            ProjectEnergy.objects.create(
                source=source,
                range_key=range_key,
                spec_hash=shash,
                spec_json=spec,
                labels=labels,
                kwh=kwh,
                total_kwh=total_kwh,
                start_unix=s,
                end_unix=e,
                step_seconds=step_s,
            )
        except Exception as db_e:
            _dbg(debug, "CACHE_SAVE_ERR", repr(db_e))

    return JsonResponse(
        {"range": range_key, "labels": labels, "kwh": kwh, "total_kwh": total_kwh, "spec": spec}
    )

def sci_score_api(request: HttpRequest) -> HttpResponse:
    """
    SCI score trend + assumptions.
    Query: range=day|month|year, optional: ci, tdp_*, embodied_*, lifetime_h
    """
    range_key = (request.GET.get("range") or "day").lower()
    if range_key not in ("day", "month", "year"):
        return HttpResponseBadRequest("range must be day|month|year")

    spec = DEFAULT_TDP_SPEC.copy()
    for key in ("cpu_count", "gpu_count"):
        if key in request.GET:
            try:
                spec[key] = int(request.GET[key])
            except Exception:
                pass
    for key in ("cpu_tdp_w", "gpu_tdp_w", "ram_w", "other_w"):
        if key in request.GET:
            try:
                spec[key] = float(request.GET[key])
            except Exception:
                pass

    embodied = DEFAULT_EMBODIED.copy()
    for key in ("cpu_kg", "gpu_kg", "system_kg"):
        if key in request.GET:
            try:
                embodied[key] = float(request.GET[key])
            except Exception:
                pass

    lifetime_h = DEFAULT_LIFETIME_HOURS
    if "lifetime_h" in request.GET:
        try:
            lifetime_h = max(1, int(request.GET["lifetime_h"]))
        except Exception:
            pass

    ci = DEFAULT_CI_G_PER_KWH
    if "ci" in request.GET:
        try:
            ci = float(request.GET["ci"])
        except Exception:
            pass

    labels, vals, avg, op_kg, emb_kg = _sci_series(range_key, spec, ci)
    op_kg_fixed, emb_kg_fixed, _ = _sci_base_per_compute_hour(spec, embodied, ci, lifetime_h)

    return JsonResponse({
        "range": range_key,
        "fu": "compute-hour",
        "labels": labels,
        "trend": [round(v, 4) for v in vals],     # kg CO2e / FU
        "avg_score": round(avg, 4),               # kg CO2e / FU (from trend)
        "operational_kg_per_fu": round(op_kg_fixed, 4),
        "embodied_kg_per_fu": round(emb_kg_fixed, 4),
        "assumptions": {
            "tdp_spec": spec,
            "embodied": embodied,
            "lifetime_h": lifetime_h,
            "ci_g_per_kwh": ci,
        },
    })

def ghg_score_api(request: HttpRequest) -> HttpResponse:
    """Minimal mock GHG 'headline' value (deterministic-ish)."""
    rng = request.GET.get("range", "day")
    base = 120.0 if rng == "day" else 3600.0 if rng == "month" else 43000.0
    today = dj_tz.now().timetuple().tm_yday
    value = round(base + (today % 5) * 1.7, 2)
    return JsonResponse({"value": value})

# -----------------------------
# SCI internals
# -----------------------------
def _power_full_watts(spec: dict) -> float:
    return (
        spec["cpu_count"] * spec["cpu_tdp_w"]
        + spec["gpu_count"] * spec["gpu_tdp_w"]
        + spec["ram_w"]
        + spec["other_w"]
    )

def _sci_seeded(seed: str = "sci") -> random.Random:
    return random.Random(seed)

def _sci_base_per_compute_hour(
    spec: dict,
    embodied: dict = DEFAULT_EMBODIED,
    ci_gpkwh: float = DEFAULT_CI_G_PER_KWH,
    lifetime_h: int = DEFAULT_LIFETIME_HOURS,
) -> Tuple[float, float, float]:
    """Return (operational_kg_per_FU, embodied_kg_per_FU, score_kg_per_FU) for FU='compute-hour'."""
    watts = _power_full_watts(spec)
    kwh_per_hour = watts / 1000.0      # 1 compute-hour at 100% util (mock)
    operational_kg = kwh_per_hour * (ci_gpkwh / 1000.0)
    embodied_total_kg = embodied["cpu_kg"] + embodied["gpu_kg"] * spec["gpu_count"] + embodied["system_kg"]
    embodied_kg = embodied_total_kg / max(1, lifetime_h)
    return operational_kg, embodied_kg, operational_kg + embodied_kg

def _sci_series(range_key: str, spec: dict, ci_gpkwh: float = DEFAULT_CI_G_PER_KWH):
    """Deterministic trend around the base value."""
    rng = _sci_seeded(f"sci-{range_key}")
    op, emb, base = _sci_base_per_compute_hour(spec, DEFAULT_EMBODIED, ci_gpkwh, DEFAULT_LIFETIME_HOURS)

    if range_key == "day":
        labels = [f"{h:02d}:00" for h in range(24)]
        vals = [max(0.01, base * (1 + rng.uniform(-0.15, 0.15))) for _ in labels]
    elif range_key == "month":
        labels = [f"D{d}" for d in range(1, 31)]
        vals = [max(0.01, base * (1 + rng.uniform(-0.12, 0.12))) for _ in labels]
    elif range_key == "year":
        labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        vals = [max(0.01, base * (1 + rng.uniform(-0.10, 0.10))) for _ in labels]
    else:
        return [], [], 0.0, 0.0, 0.0

    avg = sum(vals) / len(vals) if vals else 0.0
    return labels, vals, avg, op, emb

# -----------------------------
# Prometheus-backed energy (CPU + dynamic RAM)
# -----------------------------
def _prom_api_base(debug: bool = False) -> str:
    base = getattr(settings, "PROMETHEUS_URL", "").rstrip("/")
    api = base + "/api/v1"
    _dbg(debug, "PROM_BASE", api)
    return api

def _prom_query_range(expr: str, start: int, end: int, step: str, debug: bool = False) -> dict:
    url = _prom_api_base(debug) + "/query_range"
    _dbg(debug, "Q_RANGE", {"expr": expr, "start": start, "end": end, "step": step})
    try:
        r = requests.get(
            url,
            params={"query": expr, "start": start, "end": end, "step": step},
            timeout=60,
            verify=False,  # dev-only instance; leave False if self-signed
        )
        r.raise_for_status()
        out = r.json()
        series = len(out.get("data", {}).get("result", []))
        _dbg(debug, "Q_RANGE_OK", {"series": series, "status": out.get("status")})
        return out
    except Exception as e:
        _dbg(debug, "Q_RANGE_ERR", repr(e))
        raise

def _ts_map_from_matrix(result_obj: dict, debug: bool = False, tag: str = "") -> Dict[int, float]:
    """Sum all series into {timestamp->sum(value)}, skipping bad points."""
    series = (result_obj or {}).get("data", {}).get("result", []) or []
    acc: Dict[int, float] = {}
    for s in series:
        for item in (s.get("values") or []):
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            ts, val = item[0], item[1]
            try:
                ts_i = int(float(ts))
                v = float(val)
                if not math.isfinite(v):
                    continue
            except Exception:
                continue
            acc[ts_i] = acc.get(ts_i, 0.0) + v
    _dbg(debug, f"TS_MAP[{tag}]", {"points": len(acc)})
    return acc

def _bin_setup(range_key: str, debug: bool = False):
    now = int(time.time())
    if range_key == "day":
        step_s = 3600; start = now - 24*3600
        labels = [f"{h:02d}:00" for h in range(24)]
        def ts_to_bin(ts): return max(0, min(23, int((ts - start) // 3600)))
        bins = 24
    elif range_key == "month":
        step_s = 86400; start = now - 30*86400
        labels = [f"D{d}" for d in range(1,31)]
        def ts_to_bin(ts): return max(0, min(29, int((ts - start) // 86400)))
        bins = 30
    elif range_key == "year":
        step_s = 86400; start = now - 365*86400
        labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        def ts_to_bin(ts): return datetime.fromtimestamp(ts, tz=timezone.utc).month - 1
        bins = 12
    else:
        raise ValueError("range must be day|month|year")

    _dbg(debug, "BIN_SETUP", {"range": range_key, "start": start, "end": now, "step_s": step_s, "bins": bins})
    return start, now, step_s, labels, ts_to_bin, bins

def _prometheus_usage_series(source_key: str, range_key: str, spec: dict, debug: bool = False):
    label_val = PROJECT_TO_LABELVAL.get(source_key.lower())
    if not label_val:
        raise ValueError("Unknown source; expected clf|isis|diamond")
    _dbg(debug, "SOURCE", {"source": source_key, "label_val": label_val})

    start, end, step_s, labels, ts_to_bin, n_bins = _bin_setup(range_key, debug)
    step_str = f"{step_s}s"
    rate_win = {"day": "5m", "month": "30m", "year": "1h"}[range_key]
    _dbg(debug, "RATE_WIN", rate_win)

    expr_util  = f'avg by (instance) (1 - rate(node_cpu_seconds_total{{mode="idle",cloud_project_name="{label_val}"}}[{rate_win}]))'
    expr_cores = f'count(count by (instance, cpu) (node_cpu_seconds_total{{cloud_project_name="{label_val}"}})) by (instance)'
    expr_cpu_rich = f'sum( ({expr_util}) * on(instance) group_left() ({expr_cores}) ) * {spec["cpu_tdp_w"]}'
    _dbg(debug, "EXPR_CPU", expr_cpu_rich)

    try:
        cpu_mat = _prom_query_range(expr_cpu_rich, start, end, step_str, debug)
    except Exception as e:
        _dbg(debug, "CPU_EXPR_FALLBACK", repr(e))
        expr_cpu_fast = f'sum(rate(node_cpu_seconds_total{{mode!="idle",cloud_project_name="{label_val}"}}[{rate_win}])) * {spec["cpu_tdp_w"]}'
        _dbg(debug, "EXPR_CPU_FAST", expr_cpu_fast)
        cpu_mat = _prom_query_range(expr_cpu_fast, start, end, step_str, debug)

    expr_ram = f'sum( node_memory_Active_bytes{{cloud_project_name="{label_val}"}} / node_memory_MemTotal_bytes{{cloud_project_name="{label_val}"}} ) * {spec["ram_w"]}'
    _dbg(debug, "EXPR_RAM", expr_ram)
    ram_mat = _prom_query_range(expr_ram, start, end, step_str, debug)

    cpu_ts = _ts_map_from_matrix(cpu_mat, debug, "CPU_W")
    ram_ts = _ts_map_from_matrix(ram_mat, debug, "RAM_W")

    kwh_bins = [0.0] * n_bins
    all_ts = sorted(set(cpu_ts.keys()) | set(ram_ts.keys()))
    for ts in all_ts:
        watts = cpu_ts.get(ts, 0.0) + ram_ts.get(ts, 0.0)
        idx = ts_to_bin(ts)
        if 0 <= idx < n_bins:
            kwh_bins[idx] += (watts / 1000.0) * (step_s / 3600.0)

    _dbg(debug, "BINS_SAMPLE", {"first_5": [round(v, 3) for v in kwh_bins[:5]], "n_bins": n_bins})
    _dbg(debug, "TOTAL_KWH", round(sum(kwh_bins), 3))
    return labels, [round(v, 3) for v in kwh_bins]

# -----------------------------
# Per-workspace estimates
# -----------------------------
def _tdp_spec_for_ws(ws: dict) -> dict:
    base = DEFAULT_TDP_SPEC.copy()
    try:
        inst_specs = _stable_specs_for(ws.get("instrument") or "")
        base["cpu_count"] = int(inst_specs.get("cpus", base["cpu_count"]))
        base["gpu_count"] = int(inst_specs.get("gpus", base["gpu_count"]))
    except Exception:
        pass
    return base

def _estimate_ws_metrics(ws: dict, ci_gpkwh: float = DEFAULT_CI_G_PER_KWH) -> dict:
    """
    Dummy figures per workspace using TDP method:
      - total_kwh: sum over a simple day profile (24 hourly bins)
      - idle_kwh: assume ~12h/day at low idle watts
      - *_kg: convert with location-based CI (g/kWh -> kg)
      - idle_w: live counter power draw (W) for the idle ticker on the card
    """
    spec = _tdp_spec_for_ws(ws)
    full_watts = (
        spec["cpu_count"] * spec["cpu_tdp_w"]
        + spec["gpu_count"] * spec["gpu_tdp_w"]
        + spec["ram_w"]
        + spec["other_w"]
    )

    labels, kwh_series = _make_series("day", spec)
    total_kwh = round(sum(kwh_series), 2)

    idle_w = round(
        spec["ram_w"]
        + spec["other_w"]
        + 0.10 * (spec["cpu_count"] * spec["cpu_tdp_w"] + spec["gpu_count"] * spec["gpu_tdp_w"]),
        1,
    )
    idle_kwh = round((idle_w / 1000.0) * 12.0, 2)

    total_kg = round(total_kwh * (ci_gpkwh / 1000.0), 2)
    idle_kg = round(idle_kwh * (ci_gpkwh / 1000.0), 2)

    return {
        "tdp_spec": spec,
        "total_kwh": total_kwh, "idle_kwh": idle_kwh,
        "total_kg": total_kg,   "idle_kg": idle_kg,
        "idle_w": idle_w, "ci": ci_gpkwh,
    }

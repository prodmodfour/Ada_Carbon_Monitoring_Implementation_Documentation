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

import pandas as pd

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

from .models import ProjectEnergy, Workspace, InstrumentAverage

import plotly.graph_objects 
import plotly.io 

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

ACTIVE_WINDOW_DAYS = 30
PROJECT_LABELS = {"clf": "CLF", "isis": "ISIS", "diamond": "Diamond"}

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
    return {
        "day": 3600,                      # 1 hour
        "month": 30 * 24 * 3600,          # 30 days
        "year": 365 * 24 * 3600           # 365 days
    }[range_key]

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
    """
    Renders the main analysis page. It fetches workspace data and generates
    the INITIAL Plotly chart, which defaults to a 24-hour electricity view.
    """
    source_key = (source or "").lower()

    # Part 1: Fetch active Workspace data for each project (grouped)
    now = dj_tz.now()
    active_cutoff = now - timedelta(days=ACTIVE_WINDOW_DAYS)

    def serialize_ws(row):
        started = row.started_at or row.created_at
        elapsed_h = max(1e-6, (now - started).total_seconds() / 3600.0)
        idle_w = (row.idle_kwh / elapsed_h) * 1000.0 if elapsed_h > 0 else 0
        ci = int(row.avg_ci_g_per_kwh or 220)
        return {
            "id": str(row.id),
            "title": row.title or row.hostname or "Workspace",
            "instrument": row.instrument,
            "total_kwh": round(row.total_kwh, 3),
            "idle_kwh":  round(row.idle_kwh, 3),
            "total_kg":  round(row.total_kg, 3),
            "idle_kg":   round(row.idle_kg, 3),
            "idle_w":    round(idle_w, 1),
            "ci":        ci,
        }

    grouped = {}
    for key in ("clf", "isis", "diamond"):
        rows = (
            Workspace.objects
            .filter(source=key, updated_at__gte=active_cutoff)
            .order_by("-updated_at")[:50]
        )
        grouped[key] = {
            "label": PROJECT_LABELS.get(key, key.upper()),
            "items": [serialize_ws(w) for w in rows],
    }

    # Keep the original list for the *current* source so the rest of the view/template keeps working
    source_key = (source or "").lower()
    items = grouped.get(source_key, {"items": []})["items"]
    # Part 2: Generate the Initial Plotly Chart
    plot_div = None
    try:
        project_name = PROJECT_TO_LABELVAL.get(source_key)
        if project_name:
            df_elec = pd.read_parquet("project_estimated_electricity_usage.parquet")
            df_project = df_elec[df_elec['project_name'] == project_name].copy()
            df_project['timestamp'] = pd.to_datetime(df_project['timestamp'], utc=True)  # tz-aware
            df_project.set_index('timestamp', inplace=True)

            # last 24 hours only (tz-aware to match index)
            end = pd.Timestamp.now(tz='UTC')
            start = end - pd.Timedelta(hours=24)

            mask = (df_project.index >= start) & (df_project.index <= end)
            kwh_series = (
                pd.to_numeric(df_project.loc[mask, 'estimated_watt_hours'], errors='coerce')
                .resample('H').sum() / 1000.0
            )

            


        fig = plotly.graph_objects.Figure(
            data=[plotly.graph_objects.Bar(x=kwh_series.index, y=kwh_series, marker_color='rgba(66,133,244,0.7)')]
        )
        fig.update_layout(
            yaxis_title='Energy (kWh)',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=50, r=20, t=20, b=40),
            height=320
        )

        # Basic stats for the aside (electricity)
        total_val = float(kwh_series.sum())
        avg_val   = float(kwh_series.mean()) if len(kwh_series) else 0.0
        bins_len  = int(len(kwh_series))
        if bins_len:
            max_idx = int(kwh_series.astype(float).idxmax().value // 10**9)  # seconds since epoch (UTC)
            min_idx = int(kwh_series.astype(float).idxmin().value // 10**9)
            max_ts  = kwh_series.idxmax()
            min_ts  = kwh_series.idxmin()
            max_val = float(kwh_series.max())
            min_val = float(kwh_series.min())
            # Labels as local-friendly strings
            max_lab = max_ts.tz_convert('Europe/London').strftime('%Y-%m-%d %H:%M')
            min_lab = min_ts.tz_convert('Europe/London').strftime('%Y-%m-%d %H:%M')
        else:
            max_val = min_val = None
            max_lab = min_lab = ""

        # Plot HTML + initial sidebar update
        plot_div = plotly.io.to_html(
            fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True},
        )
        # Build the JS args safely via JSON (nulls become null, strings are quoted/escaped)
        js_args = json.dumps([
            "electricity",          # view
            total_val,              # total
            avg_val,                # avg
            bins_len,               # bins
            None if max_val is None else max_val,
            max_lab,
            None if min_val is None else min_val,
            min_lab,
        ])

        plot_div += """
        <script>
        (function(){
        const args = %s;
        if (window.updateUsageMetrics) {
            window.updateUsageMetrics.apply(null, args);
        } else {
            window.__usageInitQueue = window.__usageInitQueue || [];
            window.__usageInitQueue.push(args);
        }
        })();
        </script>
        """ % js_args

    except FileNotFoundError:
        plot_div = "<div class='chart-error'><p>Usage chart data is currently unavailable.</p></div>"
    except Exception as e:
        plot_div = f"<div class='chart-error'><p>Could not render the usage chart: {e}</p></div>"

    # Part 3: Prepare Context and Render the Full Page
    context = {
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source_key, f"{source.title()} Data Analysis"),
        "source": source_key,
        "workspaces": items,
        "workspaces_by_project": grouped,
        "usage_plot_div": plot_div,
    }
    return render(request, "analysis.html", context)


def get_usage_plot(request: HttpRequest, source: str, range_key: str, view_type: str) -> HttpResponse:
    """
    Generates and returns ONLY the HTML for the Plotly chart. This view
    is called by HTMX to dynamically update the chart based on user selection.
    """
    plot_div = "<div class='chart-error'><p>Chart data not found.</p></div>"
    source_key = source.lower()

    try:
        project_name = PROJECT_TO_LABELVAL.get(source_key)
        if project_name:
            # Step 1: Load the correct Parquet file based on the selected view_type
            if view_type == 'electricity':
                df = pd.read_parquet("project_estimated_electricity_usage.parquet")
                value_col, yaxis_title = 'estimated_watt_hours', 'Energy (kWh)'
            else:  # 'carbon'
                df = pd.read_parquet("project_carbon_footprint.parquet")
                value_col, yaxis_title = 'carbon_footprint_gCO2e', 'Emissions (kg CO₂e)'

            # Step 2: Filter to the project and index by timestamp (UTC-aware)
            df_project = df[df['project_name'] == project_name].copy()
            df_project['timestamp'] = pd.to_datetime(df_project['timestamp'], utc=True)  # <-- make tz-aware
            df_project.set_index('timestamp', inplace=True)

  
            now = pd.Timestamp.now(tz='UTC')  # <-- tz-aware to match index
            if   range_key == 'day':
                start, rule = now - pd.Timedelta(days=1), 'H'
            elif range_key == 'month':
                start, rule = now - pd.Timedelta(days=30), 'D'
            elif range_key == 'year':
                start, rule = now - pd.Timedelta(days=365), 'M'
            else:
                start, rule = now - pd.Timedelta(days=1), 'H'

            mask = (df_project.index >= start) & (df_project.index <= now)

            series = (
                pd.to_numeric(df_project.loc[mask, value_col], errors='coerce')
                .resample(rule).sum() / 1000.0
)
            # -----------------------------------------------------------------

        if series.empty:
            return HttpResponse("<div class='chart-error'><p>No data in selected range.</p></div>")

        total_val = float(series.sum())
        avg_val   = float(series.mean())
        bins_len  = int(len(series))

        # Extrema for sidebar
        if bins_len:
            max_ts  = series.idxmax()
            min_ts  = series.idxmin()
            max_val = float(series.max())
            min_val = float(series.min())
            max_lab = max_ts.tz_convert('Europe/London').strftime('%Y-%m-%d %H:%M')
            min_lab = min_ts.tz_convert('Europe/London').strftime('%Y-%m-%d %H:%M')
        else:
            max_val = min_val = None
            max_lab = min_lab = ""

        # Step 3: Create and configure the Plotly figure
        fig = plotly.graph_objects.Figure(
            data=[plotly.graph_objects.Bar(x=series.index, y=series, marker_color='rgba(66,133,244,0.7)')]
        )
        fig.update_layout(
            yaxis_title=yaxis_title,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=50, r=20, t=20, b=40),
            height=320
        )

        # Step 4: Convert to HTML.
        plot_div = plotly.io.to_html(
            fig, full_html=False, include_plotlyjs=False, config={'responsive': True},
        )

        # Append a tiny inline script to update the sidebar metrics
        # view_type is either 'electricity' (kWh) or 'carbon' (kg CO2e)
        js_args = json.dumps([
            view_type,              # "electricity" | "carbon"
            total_val,
            avg_val,
            bins_len,
            None if max_val is None else max_val,
            max_lab,
            None if min_val is None else min_val,
            min_lab,
        ])

        plot_div += """
        <script>
        (function(){
        const args = %s;
        if (window.updateUsageMetrics) {
            window.updateUsageMetrics.apply(null, args);
        } else {
            window.__usageInitQueue = window.__usageInitQueue || [];
            window.__usageInitQueue.push(args);
        }
        })();
        </script>
        """ % js_args

    except FileNotFoundError as e:
        plot_div = f"<div class='chart-error'><p>Data file not found: {e.filename}</p></div>"
    except Exception as e:
        plot_div = f"<div class='chart-error'><p>Error rendering chart: {e}</p></div>"

    return HttpResponse(plot_div)

def instruments(request: HttpRequest, source: str) -> HttpResponse:
    source_key = source.lower()
    base_list = ISIS_INSTRUMENTS if source_key == "isis" else CLF_INSTRUMENTS

    enriched = []
    now = dj_tz.now()

    for name in base_list:
        row = (
            InstrumentAverage.objects
            .filter(source=source_key, instrument=name)
            .order_by("-updated_at")
            .first()
        )

        # Use cached last-year average if it's fresh (updated within ~45 days),
        # otherwise fall back to your existing per-hour estimate.
        if row and (now - row.updated_at).total_seconds() < 45 * 24 * 3600:
            kwh_h = float(row.kwh_per_hour)
            kg_h  = float(row.kg_per_hour)
        else:
            kwh_h, kg_h = _instrument_hourly_figures(name)

        item = {"name": name, "kwh_per_hour": kwh_h, "kg_per_hour": kg_h}

        # Optional: show grams if tiny (your template supports inst.g_per_hour)
        if kg_h < 1.0:
            item["g_per_hour"] = int(round(kg_h * 1000))

        enriched.append(item)

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

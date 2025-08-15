import random, math, datetime as dt

import uuid
import urllib.request, json
from datetime import timedelta
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils import timezone
from urllib.parse import quote

def _ws_key(source: str) -> str:
    # keep workspaces separate per source (isis, clf, ...)
    return f"workspaces::{source.lower()}"

def _get_workspaces(request, source: str):
    return request.session.get(_ws_key(source), [])

def _save_workspaces(request, source: str, items):
    request.session[_ws_key(source)] = items
    request.session.modified = True

def _add_workspace(request, source: str, instrument: str):
    items = _get_workspaces(request, source)
    next_num = len(items) + 1
    items.append({
        "title": f"Workspace {next_num}",
        "owner": "Ashraf Hussain",
        "instrument": instrument,
        "created_at": timezone.now().isoformat(),
        # you can add status, kernel, etc. later
    })
    _save_workspaces(request, source, items)



def home(request: HttpRequest) -> HttpResponse:
    """Render the landing page with cards linking to analysis pages."""
    return render(request, 'home.html')


def analysis(request, source: str):
    source_key = source.lower()
    context = {
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source_key, f"{source.title()} Data Analysis"),
        "source": source,
        "workspaces": _ensure_workspace_ids(request, source),  # ensure every item has an id
    }
    return render(request, "analysis.html", context)




def instruments(request: HttpRequest, source: str) -> HttpResponse:

    source_key = source.lower()
    # Define instruments for each facility. These lists are derived from
    # the screenshots provided by the user and may be updated as needed.
    isis_instruments = [
        # ISIS instrument names extracted from the provided screenshot
        'ALF', 'ARGUS', 'CHRONUS', 'CRISP', 'EMU', 'ENGINX', 'GEM', 'HIFI', 'HRPD', 'IMAT',
        'INES', 'INTER', 'IRIS', 'LARMOR', 'LET', 'LOQ', 'MAPS', 'MARI', 'MERLIN', 'MUSR',
        'NEUTRONICS', 'NIMROD', 'NMIDG', 'OFFSPEC', 'OSIRIS', 'PEARL', 'POLARIS', 'POLREF',
        'SANDALS', 'SANS2D', 'SURF', 'SXD', 'TOSCA', 'VESUVIO', 'WISH', 'ZOOM'
    ]
    clf_instruments = ['ARTEMIS', 'EPAC', 'GEMINI', 'OCTOPUS', 'ULTRA', 'VULCAN']
    if source_key == 'isis':
        instruments = isis_instruments
    else:
        instruments = clf_instruments
    context = {
        'source_title': {
            'isis': 'ISIS Data Analysis',
            'clf': 'Central Laser Facility Data Analysis',
            'diamond': 'Diamond Data Analysis',
        }.get(source_key, f'{source.title()} Data Analysis'),
        'instruments': instruments,
        'source': source,
    }
    # Choose template based on facility; reuse same layout but lists differ.
    template_name = 'instruments_isis.html' if source_key == 'isis' else 'instruments_clf.html'
    return render(request, template_name, context)

def _stable_specs_for(instrument_name: str) -> dict:

    r = random.Random(instrument_name.lower())
    cpus = r.choice([4, 8, 12, 16, 24, 32, 48, 64])
    ram  = r.choice([16, 24, 32, 48, 64, 96, 128, 192, 256])  # GB
    gpus = r.choice([0, 1, 1, 2, 2, 4])  # weight toward 1–2 GPUs
    return {"cpus": cpus, "ram": ram, "gpus": gpus}

def instrument_detail(request, source: str, instrument: str):
    # Only redirect after a real "Create Workspace" POST
    if request.method == "POST" and request.POST.get("create_workspace") == "1":
        _add_workspace(request, source, instrument)
        return redirect('analysis', source=source)

    # GET -> render the detail page
    source_key = source.lower()
    context = {
        "source": source,
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source_key, f"{source.title()} Data Analysis"),
        "instrument_name": instrument,
        "specs": _stable_specs_for(instrument),
    }
    return render(request, "instrument_detail.html", context)

def _ws_key(source: str) -> str:
    return f"workspaces::{source.lower()}"

def _get_workspaces(request, source: str):
    return request.session.get(_ws_key(source), [])

def _save_workspaces(request, source: str, items):
    request.session[_ws_key(source)] = items
    request.session.modified = True

def _ensure_workspace_ids(request, source: str):
    """Upgrade any pre-existing session items to include a UUID id."""
    items = _get_workspaces(request, source)
    changed = False
    for ws in items:
        if 'id' not in ws:
            ws['id'] = str(uuid.uuid4())
            changed = True
    if changed:
        _save_workspaces(request, source, items)
    return items

def _get_workspace(request, source: str, ws_id: str):
    for ws in _ensure_workspace_ids(request, source):
        if ws.get('id') == ws_id:
            return ws
    return None

def _delete_workspace(request, source: str, ws_id: str):
    items = _get_workspaces(request, source)
    items = [w for w in items if w.get('id') != ws_id]
    _save_workspaces(request, source, items)

def _stable_specs_for(instrument_name: str) -> dict:
    r = random.Random(instrument_name.lower())
    cpus = r.choice([4, 8, 12, 16, 24, 32, 48, 64])
    ram  = r.choice([16, 24, 32, 48, 64, 96, 128, 192, 256])
    gpus = r.choice([0, 1, 1, 2, 2, 4])
    return {"cpus": cpus, "ram": ram, "gpus": gpus}

def _add_workspace(request, source: str, instrument: str):
    items = _get_workspaces(request, source)
    next_num = len(items) + 1
    now = timezone.now()
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

def workspace_detail(request, source: str, ws_id: str):
    ws = _get_workspace(request, source, ws_id)
    if not ws:
        return redirect('analysis', source=source)

    # Delete action
    if request.method == "POST" and request.POST.get("delete") == "1":
        _delete_workspace(request, source, ws_id)
        return redirect('analysis', source=source)

    # Touch last activity for demo purposes
    ws["last_activity"] = timezone.now().isoformat()
    items = _get_workspaces(request, source)
    for i, w in enumerate(items):
        if w.get("id") == ws_id:
            items[i] = ws
            break
    _save_workspaces(request, source, items)

    source_key = source.lower()
    context = {
        "source": source,
        "source_title": {
            "isis": "ISIS Data Analysis",
            "clf": "Central Laser Facility Data Analysis",
            "diamond": "Diamond Data Analysis",
        }.get(source_key, f"{source.title()} Data Analysis"),
        "ws": ws,
    }
    return render(request, "workspace_detail.html", context)


def ci_proxy(request):
    """
    Server-side proxy for the GB Carbon Intensity API.
    Accepts GET ?from=<ISO8601 UTC> & to=<ISO8601 UTC>
    and returns the API JSON. Avoids browser CORS issues.
    """
    frm = request.GET.get('from')
    to = request.GET.get('to')
    if not frm or not to:
        return HttpResponseBadRequest("Query params 'from' and 'to' are required.")

    base = "https://api.carbonintensity.org.uk/intensity"
    # allow :, -, T, Z characters to pass through
    safe = ":-TZ"
    url = f"{base}/{quote(frm, safe=safe)}/{quote(to, safe=safe)}"

    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read().decode(charset)
            payload = json.loads(data)
            return JsonResponse(payload)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=502)

# ---- Project usage dummy API (swap to DB later) -----------------------------

# Default TDP spec (Watts). Replace with DB values later.
DEFAULT_TDP_SPEC = {
    "cpu_count": 12,    # logical or physical; up to you
    "cpu_tdp_w": 12,    # per-core watts under typical load (not peak)
    "gpu_count": 1,
    "gpu_tdp_w": 250,   # per-GPU watts
    "ram_w": 20,        # system/ram etc
    "other_w": 30       # misc platform overhead
}

def _seeded_rng(seed="project"):
    return random.Random(seed)

def _util_profile_day(idx):
    """24*2 half-hour bins → return utilization 0..1 for hour bins we’ll build here."""
    # Simple diurnal: morning ramp, mid-day plateau, evening taper
    hour = idx
    base = 0.25 + 0.45 * math.sin((hour-8) * math.pi/12)  # peaks around mid-day
    return max(0.05, min(0.95, base))

def _make_series(range_key: str, spec: dict):
    """
    Build labels + kWh per bin for:
      - day: 24 hourly bins
      - month: 30 daily bins (dummy month)
      - year: 12 monthly bins
    """
    rng = _seeded_rng("project-usage")
    labels, kwh = [], []

    # Base device power (Watts) when "utilization==1"
    full_watts = (
        spec["cpu_count"] * spec["cpu_tdp_w"] +
        spec["gpu_count"] * spec["gpu_tdp_w"] +
        spec["ram_w"] + spec["other_w"]
    )

    if range_key == "day":
        # 24 hourly bins, utilization varies by hour
        for h in range(24):
            util = _util_profile_day(h) + rng.uniform(-0.05, 0.05)
            util = max(0.05, min(0.95, util))
            watts = full_watts * util
            kwh.append(round(watts / 1000 * 1.0, 3))  # 1 hour
            labels.append(f"{str(h).zfill(2)}:00")

    elif range_key == "month":
        # 30 days; weekday/weekend modulation
        for d in range(1, 31):
            weekday = (d % 7) not in (6, 0)  # simple pattern; replace with real calendar if needed
            util = (0.55 if weekday else 0.35) + rng.uniform(-0.08, 0.08)
            util = max(0.05, min(0.95, util))
            hours = 8 if weekday else 4  # active hours per day
            kwh.append(round(full_watts / 1000 * hours, 3))
            labels.append(f"D{d}")

    elif range_key == "year":
        # 12 months; seasonal modulation
        for m in range(1, 13):
            season = (0.6 if m in (2,3,10,11) else 0.5)  # more usage in shoulder months
            util = season + rng.uniform(-0.07, 0.07)
            util = max(0.05, min(0.95, util))
            hours = 8 * 22  # ~22 working days x 8h
            kwh.append(round(full_watts / 1000 * hours * util, 2))
            labels.append(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m-1])
    else:
        return [], []

    return labels, kwh

def project_usage_api(request):
    """
    Returns estimated electricity usage for a project.
    Query params:
      - range: day | month | year
      - view: elec | carbon   (client uses for display; server returns elec kWh)
      - (optional) tdp_* to override default spec, e.g. ?cpu_count=16&gpu_count=2...
    Replace internals with DB lookups later.
    """
    range_key = request.GET.get("range", "day").lower()
    if range_key not in ("day", "month", "year"):
        return HttpResponseBadRequest("range must be day|month|year")

    # Allow overrides via query string for quick testing
    spec = DEFAULT_TDP_SPEC.copy()
    for key in ("cpu_count","cpu_tdp_w","gpu_count","gpu_tdp_w","ram_w","other_w"):
        if key in request.GET:
            try:
                spec[key] = float(request.GET[key]) if key.endswith("_w") else int(request.GET[key])
            except ValueError:
                pass

    labels, kwh = _make_series(range_key, spec)
    total_kwh = round(sum(kwh), 3)

    return JsonResponse({
        "range": range_key,
        "labels": labels,
        "kwh": kwh,
        "total_kwh": total_kwh,
        "spec": spec,
        # Note: client will convert to CO2e using CI factors (can also be server-side later)
    })
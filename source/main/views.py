import random

import uuid
from datetime import timedelta
from django.http import HttpRequest, HttpResponse  
from django.shortcuts import render, redirect
from django.utils import timezone

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

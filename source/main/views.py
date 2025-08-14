import random

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


def analysis(request: HttpRequest, source: str) -> HttpResponse:
    source_key = source.lower()
    context = {
        'source_title': {
            'isis': 'ISIS Data Analysis',
            'clf': 'Central Laser Facility Data Analysis',
            'diamond': 'Diamond Data Analysis',
        }.get(source_key, f'{source.title()} Data Analysis'),
        'source': source,
        'workspaces': _get_workspaces(request, source),  # NEW
    }
    return render(request, 'analysis.html', context)



def instruments(request: HttpRequest, source: str) -> HttpResponse:
    """
    Display a list of instruments available for the selected data source.

    There are separate instrument lists for ISIS and for the other
    facilities (CLF and Diamond). If an unrecognised source is
    provided the view falls back to the CLF/Diamond list.
    """
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

def data_display_catalogue(request):
    # dummy-only page; all data generated in template JS
    return render(request, 'data_display_catalogue.html', {
        "page_title": "Data Display Catalogue"
    })

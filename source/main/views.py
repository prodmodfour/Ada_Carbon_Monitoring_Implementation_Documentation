import random

from django.http import HttpRequest, HttpResponse  # type: ignore
from django.shortcuts import render  # type: ignore


def home(request: HttpRequest) -> HttpResponse:
    """Render the landing page with cards linking to analysis pages."""
    return render(request, 'home.html')


def analysis(request: HttpRequest, source: str) -> HttpResponse:
    """
    Render the generic analysis page.

    The ``source`` parameter determines the heading displayed on the
    page. If an unrecognised source is provided, the heading uses the
    raw value.
    """
    title_map = {
        'ISIS': 'ISIS Data Analysis',
        'CLF': 'Central Laser Facility Data Analysis',
        'Diamond': 'Diamond Data Analysis',
    }
    context = {
        'source_title': title_map.get(source, f'{source} Data Analysis'),
        'source': source,
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
    """
    Produce a stable 'random' spec for the given instrument by seeding
    the RNG with the instrument name. This keeps values the same across reloads.
    """
    r = random.Random(instrument_name.lower())
    cpus = r.choice([4, 8, 12, 16, 24, 32, 48, 64])
    ram  = r.choice([16, 24, 32, 48, 64, 96, 128, 192, 256])  # GB
    gpus = r.choice([0, 1, 1, 2, 2, 4])  # weight toward 1–2 GPUs
    return {"cpus": cpus, "ram": ram, "gpus": gpus}

def instrument_detail(request, source: str, instrument: str):
    """
    Detail page for a chosen instrument. Specs are stable per instrument.
    """
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
"""
View functions for the Ada mock project.

Each view renders a template that approximates the look of the
corresponding page in the original system. Since this project is a
mock, these views intentionally avoid any business logic or
authentication checks.
"""

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

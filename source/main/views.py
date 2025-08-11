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
    }
    return render(request, 'analysis.html', context)

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Tuple

import requests
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone as dj_tz

from main.models import InstrumentAverage
# We reuse your existing helpers and instrument lists from views.py
from main.views import (
    CLF_INSTRUMENTS, ISIS_INSTRUMENTS,
    DEFAULT_TDP_SPEC, _stable_specs_for, _instrument_hourly_figures,
)

CI_API = "https://api.carbonintensity.org.uk/intensity"

def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    # API tolerates both Z and +00:00; force Z for readability
    return dt.strftime("%Y-%m-%dT%H:%MZ")

def _avg_ci_over_window(start: datetime, end: datetime, chunk_days: int = 7) -> float:
    """
    Average g/kWh from the UK Carbon Intensity API between [start, end).
    We chunk requests to avoid huge payloads (half-hourly series).
    """
    s = start
    vals: List[float] = []
    while s < end:
        e = min(s + timedelta(days=chunk_days), end)
        url = f"{CI_API}/{_iso_z(s)}/{_iso_z(e)}"
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = (r.json() or {}).get("data", [])
        for item in data:
            inten = item.get("intensity") or {}
            v = inten.get("actual")
            if v is None:
                v = inten.get("forecast")
            if v is not None:
                try:
                    vals.append(float(v))
                except Exception:
                    pass
        s = e
    # Fallback to a conservative 220 g/kWh if the API gave us nothing
    return sum(vals) / len(vals) if vals else 220.0

def _tdp_spec_for_instrument(name: str) -> dict:
    spec = DEFAULT_TDP_SPEC.copy()
    hw = _stable_specs_for(name)
    # Adopt your deterministic hardware choices
    spec["cpu_count"] = int(hw.get("cpus", spec["cpu_count"]))
    spec["gpu_count"] = int(hw.get("gpus", spec["gpu_count"]))
    return spec

class Command(BaseCommand):
    help = "Compute rolling last-365-day average electricity and carbon per instrument and cache them."

    def add_arguments(self, parser):
        parser.add_argument("--sources", default="clf,isis", help="Comma-separated: clf,isis,diamond")
        parser.add_argument("--days", type=int, default=365, help="Window length (default 365)")

    def handle(self, *args, **opts):
        sources = [s.strip().lower() for s in (opts["sources"] or "").split(",") if s.strip()]
        days = int(opts["days"])
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)

        src_to_instruments = {
            "clf": CLF_INSTRUMENTS,
            "isis": ISIS_INSTRUMENTS,
        }

        for src in sources:
            instruments = src_to_instruments.get(src, [])
            if not instruments:
                self.stdout.write(self.style.WARNING(f"[skip] Unknown source '{src}' or no instrument list"))
                continue

            self.stdout.write(self.style.NOTICE(f"[{src}] averaging CI {start:%Y-%m-%d} → {now:%Y-%m-%d}…"))
            avg_ci = _avg_ci_over_window(start, now)
            self.stdout.write(f"    avg CI ≈ {avg_ci:.1f} g/kWh")

            for name in instruments:
                # Use your existing per-hour TDP estimate, but feed it the *year* avg CI we just computed.
                kwh_h, kg_h = _instrument_hourly_figures(name, ci_gpkwh=avg_ci)
                spec = _tdp_spec_for_instrument(name)

                InstrumentAverage.objects.update_or_create(
                    source=src,
                    instrument=name,
                    defaults={
                        "window_start": start,
                        "window_end": now,
                        "avg_ci_g_per_kwh": float(avg_ci),
                        "kwh_per_hour": float(kwh_h),
                        "kg_per_hour": float(kg_h),
                        "tdp_spec": spec,
                    },
                )
                self.stdout.write(f"    {name:<12}  {kwh_h:>6.2f} kWh/h · {kg_h:>6.2f} kg/h")
        self.stdout.write(self.style.SUCCESS("Done."))

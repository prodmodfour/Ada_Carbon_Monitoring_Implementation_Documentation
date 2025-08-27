

from __future__ import annotations

import time
from datetime import datetime, timezone as dt_tz
from typing import Dict

import requests
from django.core.management.base import BaseCommand
from django.conf import settings

from main.models import Workspace

# Match your site→Prom label mapping (same as your views)
PROJECT_TO_LABELVAL = {
    "clf": "CDAaaS",
    "isis": "IDAaaS",
    "diamond": "DDAaaS",
}

# Simple power model (kept consistent with your mock’s assumptions)
DEFAULT_TDP_SPEC = {
    "cpu_tdp_w": 12,   # per core
    "ram_w": 20,       # W
    "other_w": 30,     # W
}
DEFAULT_CI_G_PER_KWH = 220  # fallback only

# --- Carbon Intensity (live from api.carbonintensity.org.uk) -----------------
_CI_CACHE_VAL: float | None = None
_CI_CACHE_TS: float = 0.0
_CI_CACHE_TTL_S: int = 300  # 5 minutes

def _get_ci_gpkwh() -> float:
    """
    Returns current GB grid carbon intensity in gCO2/kWh.
    Uses /intensity (current half-hour), prefers 'actual' then 'forecast'.
    Caches for 5 minutes; falls back to last value or DEFAULT if unreachable.
    """
    global _CI_CACHE_VAL, _CI_CACHE_TS
    now = time.time()
    if _CI_CACHE_VAL is not None and (now - _CI_CACHE_TS) < _CI_CACHE_TTL_S:
        return _CI_CACHE_VAL

    try:
        r = requests.get("https://api.carbonintensity.org.uk/intensity", timeout=15)
        r.raise_for_status()
        payload = r.json() or {}
        rows = payload.get("data") or []
        if rows:
            intensity = (rows[0] or {}).get("intensity") or {}
            val = intensity.get("actual")
            if val is None:
                val = intensity.get("forecast")
            if val is not None:
                _CI_CACHE_VAL = float(val)
                _CI_CACHE_TS = now
                return _CI_CACHE_VAL
    except Exception:
        pass

    # fallback: last good sample or a conservative default
    return _CI_CACHE_VAL if _CI_CACHE_VAL is not None else DEFAULT_CI_G_PER_KWH

# --- Prometheus helpers ------------------------------------------------------
def _prom_base() -> str:
    base = getattr(settings, "PROMETHEUS_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("PROMETHEUS_URL is not configured in Django settings.")
    return base + "/api/v1"

def _q(expr: str):
    # Many lab Prometheus instances use self-signed certs; disable verify in dev.
    r = requests.get(_prom_base() + "/query", params={"query": expr}, timeout=30, verify=False)
    r.raise_for_status()
    return (r.json().get("data", {}) or {}).get("result", []) or []

def _vector_to_map(rows, key_label="instance") -> Dict[str, float]:
    out: Dict[str, float] = {}
    for r in rows:
        labels = r.get("metric", {}) or {}
        inst = labels.get(key_label)
        vals = r.get("value") or r.get("values")
        if not inst or not vals:
            continue
        try:
            v = float(vals[-1][1]) if isinstance(vals, list) else float(vals[1])
        except Exception:
            continue
        out[inst] = v
    return out

# --- Command -----------------------------------------------------------------
class Command(BaseCommand):
    help = "Discover active hosts, split idle vs busy energy, and update Workspace rows each minute."

    def add_arguments(self, parser):
        parser.add_argument("--sleep", type=int, default=60, help="Seconds between polls if looping.")
        parser.add_argument("--once", action="store_true", help="Run one sync then exit.")

    def handle(self, *args, **opts):
        sleep_s = int(opts["sleep"])
        loop = not bool(opts["once"])

        self.stdout.write(self.style.NOTICE("Syncing workspaces from Prometheus…"))
        while True:
            try:
                for source, label_val in PROJECT_TO_LABELVAL.items():
                    self.sync_source(source, label_val)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"[sync] {e!r}"))

            if not loop:
                break
            time.sleep(max(1, sleep_s))

    # ----- per-site sync -----
    def sync_source(self, source: str, label_val: str):
        # 1) Active hosts (up == 1)
        hosts = set(_vector_to_map(_q(f'sum by (instance) (up{{cloud_project_name="{label_val}"}})==1')).keys())
        if not hosts:
            return

        # 2) Boot times (for started_at)
        boot = _vector_to_map(_q(f'node_boot_time_seconds{{cloud_project_name="{label_val}"}}'))

        # 3) Idle fraction over 1 minute
        idle_num = _vector_to_map(_q(
            f'sum by (instance) (rate(node_cpu_seconds_total{{mode="idle",cloud_project_name="{label_val}"}}[1m]))'
        ))
        idle_den = _vector_to_map(_q(
            f'sum by (instance) (rate(node_cpu_seconds_total{{cloud_project_name="{label_val}"}}[1m]))'
        ))
        idle_frac: Dict[str, float] = {}
        for h in hosts:
            n, d = idle_num.get(h, 0.0), idle_den.get(h, 0.0)
            idle_frac[h] = 0.0 if d <= 0 else max(0.0, min(1.0, n / d))

        # 4) CPU cores per host
        cores = _vector_to_map(_q(
            f'count(count by (instance, cpu) (node_cpu_seconds_total{{cloud_project_name="{label_val}"}})) by (instance)'
        ))

        # 5) Memory active ratio (Active / MemTotal)
        mem_active = _vector_to_map(_q(f'node_memory_Active_bytes{{cloud_project_name="{label_val}"}}'))
        mem_total  = _vector_to_map(_q(f'node_memory_MemTotal_bytes{{cloud_project_name="{label_val}"}}'))
        mem_ratio: Dict[str, float] = {}
        for h in hosts:
            a, t = mem_active.get(h, 0.0), mem_total.get(h, 0.0)
            mem_ratio[h] = 0.0 if t <= 0 else max(0.0, min(1.0, a / t))

        # 6) Upsert + accumulate per minute (with live CI)
        ci_gpkwh = _get_ci_gpkwh()
        for host in sorted(hosts):
            self._update_workspace_row(
                source=source,
                host=host,
                boot_ts=boot.get(host),
                cores=int(cores.get(host, 0)),
                idle_fraction=idle_frac.get(host, 0.0),
                mem_ratio=mem_ratio.get(host, 0.0),
                ci_gpkwh=ci_gpkwh,
            )

    def _update_workspace_row(
        self,
        *,
        source: str,
        host: str,
        boot_ts: float | None,
        cores: int,
        idle_fraction: float,
        mem_ratio: float,
        ci_gpkwh: float,
    ):
        spec = DEFAULT_TDP_SPEC
        util = 1.0 - float(idle_fraction)

        # simple power split
        cpu_w = max(0, cores) * spec["cpu_tdp_w"] * util
        ram_w = spec["ram_w"] * float(mem_ratio)
        other_w = spec["other_w"]
        watts = cpu_w + ram_w + other_w

        duration_s = 60
        kwh = (watts / 1000.0) * (duration_s / 3600.0)
        idle_kwh = kwh * float(idle_fraction)
        busy_kwh = max(0.0, kwh - idle_kwh)

        ws, _ = Workspace.objects.get_or_create(
            source=source,
            hostname=host,
            defaults={"title": host, "owner": "", "instrument": ""},
        )

        # set start time if known
        if boot_ts and not ws.started_at:
            ws.mark_started(datetime.fromtimestamp(boot_ts, tz=dt_tz.utc))

        # add busy (counts to runtime_seconds), then idle — both with live CI
        active_s = int(round(duration_s * util))
        if busy_kwh > 0:
            ws.record_usage(duration_s=active_s, energy_kwh=busy_kwh, ci_g_per_kwh=ci_gpkwh, idle=False)
        if idle_kwh > 0:
            ws.record_usage(duration_s=0, energy_kwh=idle_kwh, ci_g_per_kwh=ci_gpkwh, idle=True)

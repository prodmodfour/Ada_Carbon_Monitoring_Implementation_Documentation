from django.core.management.base import BaseCommand
from django.utils.timezone import now as tz_now

from main.models import ProjectEnergy
from main.views import (
    _prometheus_usage_series, _bin_meta,
    DEFAULT_TDP_SPEC, PROJECT_TO_LABELVAL, _spec_hash, _dbg, _cache_ttl_seconds
)

import time
import urllib3


class Command(BaseCommand):
    help = "Recompute and cache ProjectEnergy for given sources/ranges."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sources", default="clf,isis,diamond",
            help="Comma list: clf,isis,diamond"
        )
        parser.add_argument(
            "--ranges", default="day,month,year",
            help="Comma list: day,month,year"
        )
        parser.add_argument("--debug", action="store_true")
        parser.add_argument(
            "--force", action="store_true",
            help="Always write a fresh row (ignore TTL / existing cache)"
        )
        parser.add_argument(
            "--skip-fresh", action="store_true",
            help="Skip writing if latest cache row is still within TTL (default: off)"
        )

        # Optional overrides (same names as view spec keys)
        parser.add_argument("--cpu-tdp-w", type=float)
        parser.add_argument("--ram-w", type=float)
        parser.add_argument("--gpu-tdp-w", type=float)
        parser.add_argument("--cpu-count", type=float)
        parser.add_argument("--gpu-count", type=float)
        parser.add_argument("--other-w", type=float)

    def handle(self, *args, **opts):
        # Silence InsecureRequestWarning for dev-only Prometheus with verify=False
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        debug = opts["debug"]
        force = opts["force"]
        skip_fresh = opts["skip_fresh"]

        sources = [s.strip().lower() for s in opts["sources"].split(",") if s.strip()]
        ranges = [r.strip().lower() for r in opts["ranges"].split(",") if r.strip()]

        # Build spec (CLI overrides -> spec dict)
        spec = DEFAULT_TDP_SPEC.copy()
        for cli_key, spec_key in [
            ("cpu_tdp_w", "cpu_tdp_w"),
            ("ram_w", "ram_w"),
            ("gpu_tdp_w", "gpu_tdp_w"),
            ("cpu_count", "cpu_count"),
            ("gpu_count", "gpu_count"),
            ("other_w", "other_w"),
        ]:
            value = opts.get(cli_key)
            if value is not None:
                spec[spec_key] = value
        shash = _spec_hash(spec)

        total_tasks = len(sources) * len(ranges)
        self.stdout.write(f"Spec {spec} hash={shash} | Tasks: {total_tasks} ({sources} × {ranges})")

        t0 = time.time()
        done = 0
        skipped = 0
        failed = 0

        for source in sources:
            for range in ranges:
                tic = time.time()
                label = f"{source}:{range}"
                self.stdout.write(f"[RUN] {label} …")

                # Optional TTL skip (only when asked, unless --force is set)
                if not force and skip_fresh:
                    latest = (
                        ProjectEnergy.objects
                        .filter(source=source, range_key=range, spec_hash=shash)
                        .order_by("-updated_at")
                        .first()
                    )
                    if latest:
                        age_s = (tz_now() - latest.updated_at).total_seconds()
                        ttl_s = _cache_ttl_seconds(range)
                        if age_s < ttl_s:
                            self.stdout.write(f"[SKIP] {label} (fresh {int(age_s)}s < TTL {ttl_s}s) id={latest.id}")
                            skipped += 1
                            continue

                try:
                    if source not in PROJECT_TO_LABELVAL:
                            raise ValueError(
                                f"Unknown source '{source}' — no PROJECT_TO_LABELVAL mapping. "
                                "Define a Prometheus label mapping to proceed."
                            )
                    labels, kwh = _prometheus_usage_series(source, range, spec, debug)
                    total = round(sum(kwh), 3)
                    s, e, step = _bin_meta(range)

                    row = ProjectEnergy.objects.create(
                        source=source, range_key=range,
                        spec_hash=shash, spec_json=spec,
                        labels=labels, kwh=kwh, total_kwh=total,
                        start_unix=s, end_unix=e, step_seconds=step,
                    )
                    toc = time.time()
                    self.stdout.write(self.style.SUCCESS(
                        f"[OK]  {label} id={row.id} total_kWh={total} "
                        f"({len(labels)} bins) in {toc - tic:.1f}s"
                    ))
                    done += 1
                except Exception as e:
                    toc = time.time()
                    self.stderr.write(self.style.ERROR(
                        f"[FAIL] {label} after {toc - tic:.1f}s: {e}"
                    ))
                    failed += 1

        self.stdout.write(
            f"Completed {done}/{total_tasks} tasks "
            f"(skipped fresh={skipped}, failed={failed}) in {time.time() - t0:.1f}s"
        )

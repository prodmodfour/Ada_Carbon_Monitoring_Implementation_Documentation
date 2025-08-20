from django.core.management.base import BaseCommand
from django.utils.timezone import now as tz_now

from main.models import ProjectEnergy
from main.views import (
    _prometheus_usage_series, _make_series, _bin_meta,
    DEFAULT_TDP_SPEC, PROJECT_TO_LABELVAL, _spec_hash, _dbg
)

import time
import urllib3

class Command(BaseCommand):
    help = "Recompute and cache ProjectEnergy for given sources/ranges."

    def add_arguments(self, parser):
        parser.add_argument("--sources", default="clf,isis,diamond",
                            help="Comma list: clf,isis,diamond")
        parser.add_argument("--ranges", default="day,month,year",
                            help="Comma list: day,month,year")
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--force", action="store_true",
                            help="Ignore TTL; always write a fresh row")
        # Optional overrides (same names as your view spec keys)
        parser.add_argument("--cpu-tdp-w", type=float)
        parser.add_argument("--ram-w", type=float)
        parser.add_argument("--gpu-tdp-w", type=float)
        parser.add_argument("--cpu-count", type=float)
        parser.add_argument("--gpu-count", type=float)
        parser.add_argument("--other-w", type=float)

    def handle(self, *args, **opts):
        debug = opts["debug"]
        sources = [s.strip().lower() for s in opts["sources"].split(",") if s.strip()]
        ranges  = [r.strip().lower() for r in opts["ranges"].split(",") if r.strip()]

        spec = DEFAULT_TDP_SPEC.copy()
        for cli_key, spec_key in [
            ("cpu_tdp_w","cpu_tdp_w"),
            ("ram_w","ram_w"),
            ("gpu_tdp_w","gpu_tdp_w"),
            ("cpu_count","cpu_count"),
            ("gpu_count","gpu_count"),
            ("other_w","other_w"),
        ]:
            v = opts.get(cli_key)
            if v is not None:
                spec[spec_key] = v
        shash = _spec_hash(spec)

        total_tasks = len(sources) * len(ranges)
        self.stdout.write(self.style.NOTICE(
            f"Spec {spec} hash={shash} | Tasks: {total_tasks} ({sources} × {ranges})"
        ))

        t0 = time.time()
        done = 0

        for src in sources:
            for rng in ranges:
                tic = time.time()
                label = f"{src}:{rng}"
                self.stdout.write(f"[RUN] {label} …")
                try:
                    if src in PROJECT_TO_LABELVAL:
                        labels, kwh = _prometheus_usage_series(src, rng, spec, debug)
                    else:
                        labels, kwh = _make_series(rng, spec)
                    total = round(sum(kwh), 3)
                    s, e, step = _bin_meta(rng)

                    row = ProjectEnergy.objects.create(
                        source=src, range_key=rng,
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

        self.stdout.write(self.style.NOTICE(
            f"Completed {done}/{total_tasks} tasks in {time.time() - t0:.1f}s"
        ))
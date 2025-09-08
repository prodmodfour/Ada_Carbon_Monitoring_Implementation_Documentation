from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Workspace
import random
import uuid
from datetime import timedelta

class Command(BaseCommand):
    help = "Seeds the database with fake Workspace rows (no arguments)."

    def handle(self, *args, **options):
        rng = random.Random(42)
        now = timezone.now()

        sources = ["clf", "isis", "diamond"]
        instruments = {
            "clf": ["ARTEMIS", "EPAC", "GEMINI", "OCTOPUS", "ULTRA", "VULCAN"],
            "isis": ['ALF','ARGUS','CRISP','EMU','ENGINX','GEM','HIFI','HRPD','IMAT','INTER','IRIS','LARMOR','LET','LOQ','MAPS','MARI','MERLIN','MUSR','NIMROD','OFFSPEC','OSIRIS','PEARL','POLARIS','POLREF','SANDALS','SANS2D','SURF','SXD','TOSCA','WISH','ZOOM'],
            "diamond": ["I03","I04","I11","I12","I13","I19","B24","B21.1","I23","I22"]
        }

        total_created = 0

        for src in sources:
            for i in range(rng.randint(6, 12)):  # 6–12 workspaces per project
                inst = rng.choice(instruments[src])
                title = f"{src.upper()} Workspace {i+1}"
                host = f"host-{rng.randint(10,99)}-{rng.randint(0,255)}-{rng.randint(0,255)}.local"
                started_delta_days = rng.randint(1, 45)
                started_at = now - timedelta(days=started_delta_days, hours=rng.randint(0, 23))

                ws = Workspace.objects.create(
                    id=uuid.uuid4(),
                    source=src,
                    instrument=inst,
                    title=title,
                    owner="Demo User",
                    hostname=host,
                    started_at=started_at if rng.random() < 0.9 else None,  # a few never started
                    runtime_seconds=0,
                    total_kwh=0.0,
                    total_kg=0.0,
                    idle_kwh=0.0,
                    idle_kg=0.0,
                    avg_ci_g_per_kwh=None,
                    last_ci_g_per_kwh=None,
                    last_sampled_at=None,
                )

                # Build up some usage samples to land “recently updated” rows.
                # Keep it simple: 8–40 samples, 30–90 minutes between, variable energy.
                ci_g_per_kwh = rng.choice([180, 200, 220, 240, 260])
                t = started_at
                for _ in range(rng.randint(8, 40)):
                    dt_minutes = rng.randint(30, 90)
                    duration_s = dt_minutes * 60
                    # 0.05–0.50 kWh per sample; some marked idle
                    energy_kwh = round(rng.uniform(0.05, 0.50), 3)
                    idle = rng.random() < 0.35
                    ws.record_usage(
                        duration_s=duration_s,
                        energy_kwh=energy_kwh,
                        ci_g_per_kwh=ci_g_per_kwh,
                        idle=idle,
                    )
                    t += timedelta(minutes=dt_minutes)

                # Nudge updated_at within last ~60 days (so some are "inactive")
                recent_nudge_days = rng.randint(0, 60)
                ws.updated_at = now - timedelta(days=recent_nudge_days)
                ws.save(update_fields=["updated_at"])

                total_created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {total_created} workspaces."))
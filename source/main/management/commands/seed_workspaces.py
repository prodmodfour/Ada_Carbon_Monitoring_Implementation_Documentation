from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Workspace
import random, uuid
from datetime import timedelta

class Command(BaseCommand):
    help = "Seed workspaces with busy + idle usage and non-zero idle counters."

    def handle(self, *args, **opts):
        rng = random.Random(42)
        now = timezone.now()

        sources = ["clf", "isis", "diamond"]
        instruments = {
            "clf": ["ARTEMIS","EPAC","GEMINI","OCTOPUS","ULTRA","VULCAN"],
            "isis": ['ALF','ARGUS','CRISP','EMU','ENGINX','GEM','HIFI','HRPD','IMAT','INTER','IRIS','LARMOR','LET','LOQ','MAPS','MARI','MERLIN','MUSR','NIMROD','OFFSPEC','OSIRIS','PEARL','POLARIS','POLREF','SANDALS','SANS2D','SURF','SXD','TOSCA','WISH','ZOOM'],
            "diamond": ["I03","I04","I11","I12","I13","I19","B24","B21.1","I23","I22"]
        }

        total = 0
        for src in sources:
            for i in range(rng.randint(6, 10)):
                ws = Workspace.objects.create(
                    id=uuid.uuid4(),
                    source=src,
                    instrument=rng.choice(instruments[src]),
                    title=f"{src.upper()} Workspace {i+1}",
                    owner="Demo User",
                    hostname=f"host-{rng.randint(10,99)}-{rng.randint(0,255)}-{rng.randint(0,255)}.local",
                )

                ci_gpkwh = rng.choice([180, 200, 220, 240, 260])

                # Choose realistic idle wattage per project
                base_idle_w = {
                    "clf": rng.randint(70, 140),
                    "isis": rng.randint(40, 110),
                    "diamond": rng.randint(50, 120),
                }[src]

                # Make a recent idle window (60–120 min) that will continue ticking
                recent_idle_minutes = rng.randint(60, 120)
                recent_start = now - timedelta(minutes=recent_idle_minutes)

                # Start the workspace a few hours before the recent window so averages make sense
                ws.started_at = recent_start - timedelta(hours=rng.randint(2, 6))
                ws.save(update_fields=["started_at"])

                # ---- (A) Busy + idle history BEFORE the recent window ----
                t = ws.started_at
                while t < recent_start:
                    step_min = rng.randint(20, 60)
                    duration_s = step_min * 60
                    is_idle = rng.random() < 0.35  # ~35% idle in history

                    if is_idle:
                        w = base_idle_w * rng.uniform(0.9, 1.15)
                    else:
                        w = base_idle_w * rng.uniform(2.0, 6.0)  # active draw higher

                    kwh = round((w / 1000.0) * (step_min / 60.0), 4)
                    ws.record_usage(duration_s=duration_s, energy_kwh=kwh, ci_g_per_kwh=ci_gpkwh, idle=is_idle)
                    t += timedelta(minutes=step_min)

                # Ensure a non-zero idle baseline even if random history had few idle samples
                if ws.idle_kwh == 0:
                    # Add one small idle block (15 min)
                    kwh = round((base_idle_w / 1000.0) * (15 / 60.0), 4)
                    ws.record_usage(duration_s=15*60, energy_kwh=kwh, ci_g_per_kwh=ci_gpkwh, idle=True)

                # ---- (B) Recent idle streak (5–15 min cadence) so ticker starts > 0 and keeps moving ----
                t = recent_start
                while t < now:
                    step_min = rng.choice([5, 10, 15])
                    duration_s = step_min * 60
                    kwh = round((base_idle_w / 1000.0) * (step_min / 60.0), 4)
                    ws.record_usage(duration_s=duration_s, energy_kwh=kwh, ci_g_per_kwh=ci_gpkwh, idle=True)
                    t += timedelta(minutes=step_min)

                # Fresh vs stale updated_at so your "active" filter still has variety
                ws.updated_at = now - (timedelta(minutes=rng.randint(0, 45)) if rng.random() < 0.8
                                       else timedelta(days=rng.randint(31, 60)))
                ws.save(update_fields=["updated_at"])
                total += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {total} workspaces with busy+idle usage and non-zero idle counters."))

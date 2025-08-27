

from django.db import models
from django.db.models import Q, F
from django.utils import timezone
import uuid

class ProjectEnergyQuerySet(models.QuerySet):
    def latest_for(self, source: str, range_key: str, spec_hash: str):
        return (
            self.filter(source=source, range_key=range_key, spec_hash=spec_hash)
            .order_by("-updated_at")
            .first()
        )

class ProjectEnergy(models.Model):
    class Source(models.TextChoices):
        CLF = "clf", "CLF"
        ISIS = "isis", "ISIS"
        DIAMOND = "diamond", "Diamond"

    class RangeKey(models.TextChoices):
        DAY = "day", "Day"
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    source = models.CharField(max_length=16, choices=Source.choices)
    range_key = models.CharField(max_length=8, choices=RangeKey.choices)

    # We key cache by a hash of the spec (cpu_tdp_w, ram_w, etc.), so overrides make a new row.
    spec_hash = models.CharField(max_length=64, db_index=True)
    spec_json = models.JSONField()

    # Chart payload
    labels = models.JSONField()      # list[str]
    kwh = models.JSONField()         # list[float]
    total_kwh = models.FloatField()

    # Meta about the time window we used
    start_unix = models.BigIntegerField()
    end_unix = models.BigIntegerField()
    step_seconds = models.IntegerField()

    # Bookkeeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Manager
    objects = ProjectEnergyQuerySet.as_manager()

    class Meta:
        # Default newest-first everywhere
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["source", "range_key", "spec_hash", "-updated_at"]),
        ]
        # `unique_together` intentionally omitted (we keep history)

    def __str__(self):
        return f"{self.source}:{self.range_key}@{self.updated_at:%Y-%m-%d %H:%M:%S}"

    # Basic integrity checks (DB-enforced)
    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["source", "range_key", "spec_hash", "-updated_at"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(total_kwh__gte=0), name="total_kwh_nonneg"),
            models.CheckConstraint(check=Q(step_seconds__gt=0), name="step_seconds_pos"),
            models.CheckConstraint(check=Q(start_unix__lte=F("end_unix")), name="start_le_end"),
        ]

    # Optional: keep payload arrays aligned
    def clean(self):
        if isinstance(self.labels, list) and isinstance(self.kwh, list):
            if len(self.labels) != len(self.kwh):
                raise models.ValidationError("labels and kwh must be the same length.")


class Workspace(models.Model):
    """
    Persistent metrics for a single analysis workspace.

    All *kg* values are CO2e. "Idle" reflects time spent at/near idle draw.
    """
    # Identity / context (optional but handy if you later want to persist more than session)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(
        max_length=16,
        choices=(("clf", "CLF"), ("isis", "ISIS"), ("diamond", "Diamond")),
        help_text="Project/source this workspace belongs to (matches views).",
        db_index=True,
    )
    instrument = models.CharField(max_length=64, blank=True, default="")
    title = models.CharField(max_length=128, default="Workspace")
    owner = models.CharField(max_length=128, blank=True, default="")
    hostname = models.CharField(max_length=255, blank=True, default="")


    
    # When this workspace actually began compute activity (UTC)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)


    # Headline metrics
    runtime_seconds = models.BigIntegerField(default=0)    # total "active" runtime
    total_kwh       = models.FloatField(default=0.0)
    total_kg        = models.FloatField(default=0.0)       # CO2e for total_kwh

    idle_kwh        = models.FloatField(default=0.0)
    idle_kg         = models.FloatField(default=0.0)       # CO2e for idle_kwh

    # Carbon intensity bookkeeping (optional; helps auditing)
    # store the average CI (g/kWh) used so far and the latest sample applied
    avg_ci_g_per_kwh = models.FloatField(null=True, blank=True)
    last_ci_g_per_kwh = models.FloatField(null=True, blank=True)
    last_sampled_at = models.DateTimeField(null=True, blank=True)

    # Bookkeeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["source", "-updated_at"]),
            models.Index(fields=["instrument", "-updated_at"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(runtime_seconds__gte=0), name="ws_runtime_nonneg"),
            models.CheckConstraint(check=Q(total_kwh__gte=0),       name="ws_total_kwh_nonneg"),
            models.CheckConstraint(check=Q(total_kg__gte=0),        name="ws_total_kg_nonneg"),
            models.CheckConstraint(check=Q(idle_kwh__gte=0),        name="ws_idle_kwh_nonneg"),
            models.CheckConstraint(check=Q(idle_kg__gte=0),         name="ws_idle_kg_nonneg"),
        ]

    def __str__(self):
        return f"{self.title} [{self.source}] · {self.total_kwh:.2f} kWh / {self.total_kg:.2f} kg"

    # ---------- helpers ----------
    @property
    def time_started(self):
        return self.started_at

    def mark_started(self, ts=None):
        """Set start time once, if not already set."""
        if not self.started_at:
            self.started_at = ts or timezone.now()
            self.save(update_fields=["started_at", "updated_at"])


    @property
    def runtime_hours(self) -> float:
        return round(self.runtime_seconds / 3600.0, 3)

    def _ci_to_kg(self, kwh: float, ci_g_per_kwh: float | None) -> float:
        """Convert energy to CO2e kg using a CI value (g/kWh)."""
        if not ci_g_per_kwh:
            return 0.0
        return max(0.0, float(kwh) * float(ci_g_per_kwh) / 1000.0)

    def record_usage(
        self,
        *,
        duration_s: int,
        energy_kwh: float,
        ci_g_per_kwh: float | None = None,
        idle: bool = False,
    ) -> None:
        """
        Increment totals by a single sample.
        - duration_s: seconds represented by this sample
        - energy_kwh: energy consumed in that period
        - ci_g_per_kwh: (optional) carbon intensity applied to that energy
        - idle: mark the energy as idle vs total

        If CI is not supplied, only kWh totals are updated (kg stays as-is).
        """
        duration_s = int(max(0, duration_s))
        energy_kwh = float(max(0.0, energy_kwh))

        self.runtime_seconds += duration_s if not idle else 0
        self.total_kwh += energy_kwh
        if idle:
            self.idle_kwh += energy_kwh

        if ci_g_per_kwh is not None:
            kg = self._ci_to_kg(energy_kwh, ci_g_per_kwh)
            self.total_kg += kg
            if idle:
                self.idle_kg += kg

            # Maintain a running average CI for transparency
            # (weighted by kWh so far, excluding this sample if total_kwh==0)
            prev_kwh = max(1e-12, self.total_kwh)  # avoid div-by-zero
            # naive kWh-weighted average; good enough for dashboards
            if self.avg_ci_g_per_kwh is None:
                self.avg_ci_g_per_kwh = float(ci_g_per_kwh)
            else:
                self.avg_ci_g_per_kwh = float(
                    ((prev_kwh - energy_kwh) * (self.avg_ci_g_per_kwh or 0.0) + energy_kwh * ci_g_per_kwh)
                    / prev_kwh
                )
            self.last_ci_g_per_kwh = float(ci_g_per_kwh)
            self.last_sampled_at = timezone.now()

        self.save(update_fields=[
            "runtime_seconds", "total_kwh", "total_kg",
            "idle_kwh", "idle_kg",
            "avg_ci_g_per_kwh", "last_ci_g_per_kwh", "last_sampled_at",
            "updated_at",
        ])


class InstrumentAverage(models.Model):
    """
    Rolling last-365-day average figures for a single instrument.
    We keep history by always updating the latest row; feel free to
    keep multiple rows if you want to see drift over time.
    """
    source = models.CharField(
        max_length=16,
        choices=(("clf", "CLF"), ("isis", "ISIS"), ("diamond", "Diamond")),
        db_index=True,
    )
    instrument = models.CharField(max_length=64, db_index=True)

    # Window we averaged over (UTC)
    window_start = models.DateTimeField()
    window_end   = models.DateTimeField()

    # Results
    avg_ci_g_per_kwh = models.FloatField()   # g/kWh over the window
    kwh_per_hour     = models.FloatField()   # TDP-estimated draw while in use
    kg_per_hour      = models.FloatField()   # kWh/h * (avg CI)/1000

    # What we used to compute the TDP estimate (for transparency)
    tdp_spec = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["source", "instrument", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source}:{self.instrument} · {self.kwh_per_hour:.2f} kWh/h · {self.kg_per_hour:.2f} kg/h"



from django.db import models
from django.db.models import Q, F
from django.utils import timezone
import uuid




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
    source = models.CharField(
        max_length=16,
        choices=(("clf", "CLF"), ("isis", "ISIS"), ("diamond", "Diamond")),
        db_index=True,
    )
    instrument = models.CharField(max_length=128, db_index=True)

    window_start = models.DateTimeField()
    window_end   = models.DateTimeField()

    # Year-average CI (g/kWh) and derived hourly figures
    avg_ci_g_per_kwh = models.FloatField()
    kwh_per_hour     = models.FloatField()
    kg_per_hour      = models.FloatField()

    # For transparency/debugging
    tdp_spec   = models.JSONField(default=dict)     # the spec used if util→TDP path
    prom_meta  = models.JSONField(default=dict)     # which query we ran, step, samples, etc.

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["source", "instrument", "-updated_at"])]

    def __str__(self):
        return f"{self.source}:{self.instrument} · {self.kwh_per_hour:.2f} kWh/h · {self.kg_per_hour:.2f} kg/h"

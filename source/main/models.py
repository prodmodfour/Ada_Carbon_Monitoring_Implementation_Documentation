from django.db import models
from django.db.models import Q, F

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

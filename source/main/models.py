from django.db import models

class ProjectEnergy(models.Model):
    SOURCE_CHOICES = [
        ("clf", "CLF"),
        ("isis", "ISIS"),
        ("diamond", "Diamond"),
    ]
    RANGE_CHOICES = [
        ("day", "Day"),
        ("month", "Month"),
        ("year", "Year"),
    ]

    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    range_key = models.CharField(max_length=8, choices=RANGE_CHOICES)

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

    class Meta:
        indexes = [
            models.Index(fields=["source", "range_key", "spec_hash", "-updated_at"]),
        ]
        unique_together = ()  # allow multiple versions over time

    def __str__(self):
        return f"{self.source}:{self.range_key}@{self.updated_at:%Y-%m-%d %H:%M:%S}"

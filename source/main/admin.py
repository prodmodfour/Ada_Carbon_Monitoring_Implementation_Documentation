# main/admin.py
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
import json

from .models import ProjectEnergy

@admin.register(ProjectEnergy)
class ProjectEnergyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "source", "range_key", "spec_short", "points", "total_kwh", "updated_at", "age"
    )
    list_filter = ("source", "range_key", "updated_at")
    search_fields = ("id", "spec_hash")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_per_page = 50

    readonly_fields = (
        "source", "range_key", "spec_hash", "spec_json",
        "labels", "kwh", "total_kwh",
        "start_unix", "end_unix", "step_seconds",
        "created_at", "updated_at",
    )
    fieldsets = (
        ("Key", {"fields": ("source", "range_key", "spec_hash", "spec_json")}),
        ("Chart payload", {"fields": ("labels", "kwh", "total_kwh")}),
        ("Window", {"fields": ("start_unix", "end_unix", "step_seconds")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    actions = ["export_as_json"]

    def get_queryset(self, request):
        # Keep changelist snappy by not loading big JSON fields there
        qs = super().get_queryset(request)
        return qs.defer("labels", "kwh", "spec_json")

    @admin.display(description="Spec")
    def spec_short(self, obj: ProjectEnergy):
        try:
            s = obj.spec_json or {}
            return (
                f"CPU{int(s.get('cpu_count', 0))}×{int(s.get('cpu_tdp_w', 0))}W · "
                f"GPU{int(s.get('gpu_count', 0))}×{int(s.get('gpu_tdp_w', 0))}W · "
                f"RAM {int(s.get('ram_w', 0))}W"
            )
        except Exception:
            return "-"

    @admin.display(description="#pts")
    def points(self, obj: ProjectEnergy):
        try:
            return len(obj.kwh or [])
        except Exception:
            return 0

    @admin.display(description="Age")
    def age(self, obj: ProjectEnergy):
        delta = timezone.now() - obj.updated_at
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            return f"{int(delta.total_seconds())}s"
        hrs, mins = divmod(mins, 60)
        return f"{hrs}h {mins}m" if hrs else f"{mins}m"

    def has_add_permission(self, request):
        # Rows are created by the app, not by hand
        return False

    def export_as_json(self, request, queryset):
        """Download selected rows as a JSON array (for debugging/sharing)."""
        payload = []
        for obj in queryset:
            payload.append({
                "id": obj.pk,
                "source": obj.source,
                "range_key": obj.range_key,
                "spec_hash": obj.spec_hash,
                "spec_json": obj.spec_json,
                "labels": obj.labels,
                "kwh": obj.kwh,
                "total_kwh": obj.total_kwh,
                "start_unix": obj.start_unix,
                "end_unix": obj.end_unix,
                "step_seconds": obj.step_seconds,
                "created_at": obj.created_at.isoformat(),
                "updated_at": obj.updated_at.isoformat(),
            })
        content = json.dumps(payload, indent=2)
        stamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        resp = HttpResponse(content, content_type="application/json")
        resp["Content-Disposition"] = f'attachment; filename="projectenergy-{stamp}.json"'
        return resp

    export_as_json.short_description = "Export selected rows as JSON"

admin.site.site_header = "Mock ADA — Energy Cache"
admin.site.site_title = "Mock ADA Admin"
admin.site.index_title = "Administration"

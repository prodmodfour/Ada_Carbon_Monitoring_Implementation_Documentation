from django.contrib import admin
from .models import ProjectEnergy

@admin.register(ProjectEnergy)
class ProjectEnergyAdmin(admin.ModelAdmin):
    list_display = ("source","range_key","total_kwh","updated_at","spec_hash")
    list_filter  = ("source","range_key")
    search_fields = ("spec_hash",)
    ordering = ("-updated_at",)

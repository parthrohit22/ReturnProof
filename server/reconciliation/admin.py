from django.contrib import admin

from .models import ReconciliationRun


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("return_id", "summary_status", "scenario_name", "created_at")
    list_filter = ("summary_status",)
    search_fields = ("return_id", "scenario_name")
    readonly_fields = ("id", "input_payload", "audit_report", "created_at", "updated_at")
    ordering = ("-created_at",)

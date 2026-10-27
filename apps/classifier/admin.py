from django.contrib import admin
from .models import AnalysisRecord

@admin.register(AnalysisRecord)
class AnalysisRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'predicted_class_es', 'confidence_pct', 'is_healthy', 'user', 'created_at')
    list_filter = ('predicted_class_es', 'is_healthy', 'created_at')
    search_fields = ('predicted_class_es', 'predicted_class', 'original_filename', 'user__username')
    readonly_fields = ('created_at', 'inference_time_ms', 'model_version', 'probabilities_json')

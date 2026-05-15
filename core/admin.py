from django.contrib import admin
from .models import Camera, CrimeAlert, VideoUpload, PoliceNotification

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['camera_id', 'location', 'status', 'installed_date', 'last_active']
    list_filter = ['status', 'installed_date']
    search_fields = ['camera_id', 'location']
    list_editable = ['status']
    readonly_fields = ['installed_date', 'last_active']
    fieldsets = (
        ('Camera Information', {
            'fields': ('camera_id', 'location', 'status')
        }),
        ('Location Details', {
            'fields': ('latitude', 'longitude', 'ip_address')
        }),
        ('System Info', {
            'fields': ('installed_date', 'last_active'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CrimeAlert)
class CrimeAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_id', 'crime_type', 'location', 'confidence_score', 'status', 'timestamp']
    list_filter = ['crime_type', 'status', 'timestamp']
    search_fields = ['alert_id', 'location', 'description']
    readonly_fields = ['alert_id', 'timestamp']
    actions = ['mark_as_investigating', 'mark_as_resolved']
    
    def mark_as_investigating(self, request, queryset):
        queryset.update(status='investigating')
    mark_as_investigating.short_description = "Mark selected alerts as Investigating"
    
    def mark_as_resolved(self, request, queryset):
        queryset.update(status='resolved')
    mark_as_resolved.short_description = "Mark selected alerts as Resolved"

@admin.register(VideoUpload)
class VideoUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'uploaded_by', 'uploaded_at', 'analyzed', 'has_crime_alert']
    list_filter = ['analyzed', 'uploaded_at']
    search_fields = ['uploaded_by__username']
    readonly_fields = ['uploaded_at']
    
    def has_crime_alert(self, obj):
        return bool(obj.crime_alert)
    has_crime_alert.boolean = True
    has_crime_alert.short_description = 'Crime Detected'

@admin.register(PoliceNotification)
class PoliceNotificationAdmin(admin.ModelAdmin):
    list_display = ['alert', 'sent_at', 'notification_type', 'delivered']
    list_filter = ['notification_type', 'delivered', 'sent_at']
    search_fields = ['alert__alert_id', 'sent_to']
    readonly_fields = ['sent_at']
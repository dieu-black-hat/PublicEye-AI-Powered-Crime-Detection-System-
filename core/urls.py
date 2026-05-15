from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # ============================================================
    # MAIN PAGES
    # ============================================================
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cameras/', views.camera_feed, name='camera_feed'),
    path('upload/', views.upload_video, name='upload_video'),
    path('alerts/', views.alerts, name='alerts'),
    path('alert/<str:alert_id>/', views.alert_detail, name='alert_detail'),
    
    # ============================================================
    # ANALYTICS & REPORTS
    # ============================================================
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('api/analytics/data/', views.analytics_api_data, name='analytics_api_data'),
    path('api/analytics/export/<str:format>/', views.export_analytics, name='export_analytics'),
    
    # ============================================================
    # CAMERA MANAGEMENT
    # ============================================================
    path('manage-cameras/', views.manage_cameras, name='manage_cameras'),
    path('stream/<str:camera_id>/', views.live_camera_stream, name='live_stream'),
    
    # ============================================================
    # UPLOAD MANAGEMENT
    # ============================================================
    path('upload/status/<int:upload_id>/', views.upload_status, name='upload_status'),
    path('upload/delete/<int:upload_id>/', views.delete_upload, name='delete_upload'),
    
    # ============================================================
    # API ENDPOINTS
    # ============================================================
    path('api/stats/', views.get_crime_stats, name='api_stats'),
    path('api/export/', views.export_alerts, name='export_alerts'),
    path('api/webhook/', views.webhook_receive_alert, name='webhook'),
    
    # ============================================================
    # AUTHENTICATION
    # ============================================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]

# URL Patterns Reference:
# ============================================================
# | URL Pattern                          | Name                | Description                         |
# ============================================================
# | /                                    | home                | Home page                           |
# | /dashboard/                          | dashboard           | Police dashboard                    |
# | /cameras/                            | camera_feed         | Camera listing                      |
# | /upload/                             | upload_video        | Video upload & analysis             |
# | /alerts/                             | alerts              | All crime alerts                    |
# | /alert/<str:alert_id>/               | alert_detail        | Alert details                       |
# | /analytics/                          | analytics_dashboard | Analytics & charts dashboard        |
# | /api/analytics/data/                 | analytics_api_data  | Dynamic analytics data API          |
# | /api/analytics/export/<format>/      | export_analytics    | Export analytics (json/csv)         |
# | /manage-cameras/                     | manage_cameras      | Camera management                   |
# | /stream/<str:camera_id>/             | live_stream         | Live camera feed                    |
# | /upload/status/<int:upload_id>/      | upload_status       | Upload status API                   |
# | /upload/delete/<int:upload_id>/      | delete_upload       | Delete upload                       |
# | /api/stats/                          | api_stats           | Crime statistics API                |
# | /api/export/                         | export_alerts       | Export alerts CSV                   |
# | /api/webhook/                        | webhook             | Webhook endpoint                    |
# | /login/                              | login               | Login page                          |
# | /logout/                             | logout              | Logout                              |
# ============================================================

# Helper function to get URL by name (useful for templates)
def get_url_name(name):
    """Return full URL name with namespace"""
    return f'core:{name}'

# Example usage in templates:
# {% url 'core:dashboard' %}
# {% url 'core:analytics_dashboard' %}
# {% url 'core:analytics_api_data' %}?days=30
# {% url 'core:export_analytics' 'csv' %}?days=30
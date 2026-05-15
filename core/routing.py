# core/routing.py
"""
WebSocket URL routing for the core app.
"""

from django.urls import re_path
from . import consumers

# Define WebSocket URL patterns
websocket_urlpatterns = [
    # Main alerts WebSocket (for real-time crime alerts)
    re_path(r'ws/alerts/$', consumers.AlertConsumer.as_asgi()),
    re_path(r'ws/alerts/?$', consumers.AlertConsumer.as_asgi()),
    
    # Camera stream WebSocket (for live camera monitoring)
    re_path(r'ws/camera/(?P<camera_id>[-\w]+)/$', consumers.CameraStreamConsumer.as_asgi()),
    
    # Dashboard WebSocket (for real-time dashboard updates)
    re_path(r'ws/dashboard/$', consumers.DashboardConsumer.as_asgi()),
    re_path(r'ws/dashboard/?$', consumers.DashboardConsumer.as_asgi()),
]

print(f"✅ Loaded {len(websocket_urlpatterns)} WebSocket routes")
# publiceye/asgi.py
"""
ASGI config for publiceye project.
Handles both HTTP requests and WebSocket connections for real-time alerts.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publiceye.settings')

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# Import WebSocket URL patterns
try:
    from core.routing import websocket_urlpatterns
except ImportError:
    websocket_urlpatterns = []
    print("Warning: core.routing not found. Creating default routing.")

# If no websocket_urlpatterns, create empty list
if not websocket_urlpatterns:
    websocket_urlpatterns = []

# Define the ASGI application
application = ProtocolTypeRouter({
    # HTTP requests go to Django's ASGI handler
    "http": django_asgi_app,
    
    # WebSocket requests go to the WebSocket handler
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})

print("✅ PublicEye ASGI Application Initialized")
print(f"   WebSocket routes loaded: {len(websocket_urlpatterns)}")
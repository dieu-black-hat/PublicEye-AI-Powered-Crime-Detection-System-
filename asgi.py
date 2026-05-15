# publiceye/asgi.py
"""
ASGI config for publiceye project.

This file configures the ASGI application for both HTTP and WebSocket connections.
It enables real-time crime alerts and live camera streaming via WebSockets.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Set the default settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'publiceye.settings')

# Import WebSocket URL patterns from core app
try:
    from core.routing import websocket_urlpatterns
except ImportError:
    # Fallback if routing file doesn't exist yet
    websocket_urlpatterns = []
    print("Warning: core.routing not found. WebSocket support may be limited.")

# Define the ASGI application
application = ProtocolTypeRouter({
    # HTTP connections (traditional Django views)
    "http": get_asgi_application(),
    
    # WebSocket connections (real-time features)
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})

# Optional: Log application startup
print("✅ PublicEye ASGI Application initialized")
print(f"   - WebSocket URL patterns loaded: {len(websocket_urlpatterns)}")
print("   - Real-time crime alerts enabled")

# For debugging - show loaded WebSocket routes
def debug_websocket_routes():
    """Helper function to debug WebSocket routes"""
    if websocket_urlpatterns:
        print("\n📡 Loaded WebSocket Routes:")
        for pattern in websocket_urlpatterns:
            print(f"   - {pattern.pattern}")
    else:
        print("\n⚠️ No WebSocket routes loaded")

# Uncomment for debugging
# debug_websocket_routes()
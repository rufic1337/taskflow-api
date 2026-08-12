"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.
Routes plain HTTP to Django as usual, and WebSocket connections under
``/ws/`` to the Channels consumers, authenticated via JWT (see
``realtime.middleware.JWTAuthMiddleware``).

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.asgi import get_asgi_application

# get_asgi_application() must run before importing anything that touches
# Django models/apps (e.g. our routing, which imports consumers), otherwise
# Django raises AppRegistryNotReady.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter

from realtime.middleware import JWTAuthMiddleware
from realtime.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
})

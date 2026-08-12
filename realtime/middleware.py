from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser


class JWTAuthMiddleware(BaseMiddleware):
    """
    Channels middleware that authenticates WebSocket connections using a
    SimpleJWT access token passed as a `?token=` query string parameter
    (there's no cookie/header handshake for raw WebSocket clients).
    Falls back to AnonymousUser on any failure instead of raising, so the
    consumer is always responsible for rejecting unauthenticated scopes.
    """

    async def __call__(self, scope, receive, send):
        scope["user"] = await self._get_user(scope)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user(self, scope):
        from rest_framework_simplejwt.tokens import AccessToken

        from users.models import User

        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        if not token:
            return AnonymousUser()

        try:
            validated_token = AccessToken(token)
            return User.objects.get(id=validated_token["user_id"])
        except Exception:
            return AnonymousUser()

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class BoardConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope["url_route"]["kwargs"]["board_id"]
        self.group_name = f"board_{self.board_id}"

        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=4001)
            return

        is_member = await self._is_workspace_member(user, self.board_id)
        if not is_member:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def board_event(self, event):
        """Handler for messages of type 'board.event' sent via the channel layer."""
        await self.send_json({"event": event["event"], "data": event["data"]})

    @database_sync_to_async
    def _is_workspace_member(self, user, board_id):
        from boards.models import Board
        from workspaces.models import Membership

        board = Board.objects.filter(id=board_id).select_related("workspace").first()
        if board is None:
            return False
        return Membership.objects.filter(workspace=board.workspace, user=user).exists()

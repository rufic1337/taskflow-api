from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_board_event(board_id, event_type, data):
    """
    Push a server-side event to every WebSocket client currently connected to
    board `board_id`. Safe to call from plain synchronous DRF views.

    `event_type` is one of task.created / task.updated / task.deleted /
    comment.created. `data` should already be JSON-safe (e.g. the `.data` of
    a DRF serializer).
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"board_{board_id}",
        {"type": "board.event", "event": event_type, "data": data},
    )

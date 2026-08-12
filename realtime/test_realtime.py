import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from boards.factories import BoardFactory
from config.asgi import application
from realtime.utils import broadcast_board_event
from users.factories import UserFactory
from workspaces.factories import MembershipFactory, WorkspaceFactory
from workspaces.models import Membership


@database_sync_to_async
def _create_board_with_owner():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
    board = BoardFactory(workspace=workspace, created_by=owner)
    return owner, board


@database_sync_to_async
def _create_user():
    return UserFactory()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_member_connects_and_receives_broadcast():
    owner, board = await _create_board_with_owner()
    token = str(AccessToken.for_user(owner))

    communicator = WebsocketCommunicator(application, f"/ws/boards/{board.id}/?token={token}")
    connected, _ = await communicator.connect()
    assert connected

    # broadcast_board_event uses async_to_sync internally, which cannot run in
    # a thread that already has a running event loop (the test's own loop) —
    # dispatch it to a worker thread, exactly like a synchronous DRF view call
    # would run outside of any event loop.
    await asyncio.to_thread(
        broadcast_board_event, board.id, "task.created", {"id": 1, "title": "Write docs"}
    )

    message = await communicator.receive_json_from(timeout=5)
    assert message["event"] == "task.created"
    assert message["data"]["title"] == "Write docs"

    await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_non_member_connection_is_rejected():
    owner, board = await _create_board_with_owner()
    outsider = await _create_user()
    token = str(AccessToken.for_user(outsider))

    communicator = WebsocketCommunicator(application, f"/ws/boards/{board.id}/?token={token}")
    connected, close_code = await communicator.connect()
    assert not connected
    assert close_code == 4003


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_anonymous_connection_is_rejected():
    owner, board = await _create_board_with_owner()

    communicator = WebsocketCommunicator(application, f"/ws/boards/{board.id}/")
    connected, close_code = await communicator.connect()
    assert not connected
    assert close_code == 4001

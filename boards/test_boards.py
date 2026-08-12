import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.factories import UserFactory
from workspaces.factories import MembershipFactory, WorkspaceFactory
from workspaces.models import Membership

from .models import Board

pytestmark = pytest.mark.django_db


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def member_workspace():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
    return owner, workspace


class TestBoardCreate:
    def test_creating_board_auto_creates_default_columns(self):
        owner, workspace = member_workspace()
        client = authed_client(owner)
        response = client.post(
            reverse("board-list"), {"workspace": workspace.id, "name": "Launch Plan"}
        )
        assert response.status_code == status.HTTP_201_CREATED

        board = Board.objects.get(name="Launch Plan")
        columns = list(board.columns.order_by("position").values_list("name", "position"))
        assert columns == [("To Do", 0), ("In Progress", 1), ("Done", 2)]

    def test_non_member_cannot_create_board_on_workspace(self):
        _, workspace = member_workspace()
        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.post(
            reverse("board-list"), {"workspace": workspace.id, "name": "Sneaky Board"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestBoardVisibility:
    def test_non_member_cannot_view_boards(self):
        owner, workspace = member_workspace()
        client_owner = authed_client(owner)
        client_owner.post(reverse("board-list"), {"workspace": workspace.id, "name": "Roadmap"})

        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.get(reverse("board-list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_member_can_filter_boards_by_workspace(self):
        owner, workspace = member_workspace()
        client = authed_client(owner)
        client.post(reverse("board-list"), {"workspace": workspace.id, "name": "Roadmap"})

        response = client.get(reverse("board-list"), {"workspace": workspace.id})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

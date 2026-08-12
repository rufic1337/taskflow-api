import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from notifications.models import Notification
from users.factories import UserFactory
from workspaces.factories import MembershipFactory, WorkspaceFactory
from workspaces.models import Membership

from .factories import BoardFactory, ColumnFactory, TaskFactory
from .models import Task

pytestmark = pytest.mark.django_db


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_board_with_columns():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
    board = BoardFactory(workspace=workspace, created_by=owner)
    todo = ColumnFactory(board=board, name="To Do", position=0)
    in_progress = ColumnFactory(board=board, name="In Progress", position=1)
    return owner, workspace, board, todo, in_progress


class TestTaskCreate:
    def test_member_can_create_task(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        client = authed_client(owner)
        response = client.post(
            reverse("task-list"),
            {"board": board.id, "column": todo.id, "title": "Write README", "priority": "high"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Task.objects.filter(title="Write README").exists()

    def test_non_member_cannot_create_task(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.post(
            reverse("task-list"),
            {"board": board.id, "column": todo.id, "title": "Sneaky Task"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assigning_task_on_create_sends_notification(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        assignee = UserFactory()
        MembershipFactory(workspace=workspace, user=assignee, role=Membership.Role.MEMBER)

        client = authed_client(owner)
        response = client.post(
            reverse("task-list"),
            {
                "board": board.id,
                "column": todo.id,
                "title": "Design homepage",
                "assignee_id": assignee.id,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Notification.objects.filter(recipient=assignee, task_id=response.data["id"]).exists()


class TestTaskUpdate:
    def test_member_can_update_task(self):
        owner, workspace, board, todo, in_progress = make_board_with_columns()
        task = TaskFactory(board=board, column=todo, created_by=owner)

        client = authed_client(owner)
        response = client.patch(
            reverse("task-detail", kwargs={"pk": task.pk}), {"column": in_progress.id}
        )
        assert response.status_code == status.HTTP_200_OK
        task.refresh_from_db()
        assert task.column_id == in_progress.id

    def test_reassigning_task_sends_notification(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        assignee = UserFactory()
        MembershipFactory(workspace=workspace, user=assignee, role=Membership.Role.MEMBER)
        task = TaskFactory(board=board, column=todo, created_by=owner)

        client = authed_client(owner)
        response = client.patch(
            reverse("task-detail", kwargs={"pk": task.pk}), {"assignee_id": assignee.id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(recipient=assignee, task=task).exists()


class TestTaskDelete:
    def test_creator_can_delete_own_task(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        member = UserFactory()
        MembershipFactory(workspace=workspace, user=member, role=Membership.Role.MEMBER)
        task = TaskFactory(board=board, column=todo, created_by=member)

        client = authed_client(member)
        response = client.delete(reverse("task-detail", kwargs={"pk": task.pk}))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_plain_member_cannot_delete_others_task(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        creator = UserFactory()
        MembershipFactory(workspace=workspace, user=creator, role=Membership.Role.MEMBER)
        other_member = UserFactory()
        MembershipFactory(workspace=workspace, user=other_member, role=Membership.Role.MEMBER)
        task = TaskFactory(board=board, column=todo, created_by=creator)

        client = authed_client(other_member)
        response = client.delete(reverse("task-detail", kwargs={"pk": task.pk}))
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Task.objects.filter(pk=task.pk).exists()

    def test_workspace_owner_can_delete_any_task(self):
        owner, workspace, board, todo, _ = make_board_with_columns()
        member = UserFactory()
        MembershipFactory(workspace=workspace, user=member, role=Membership.Role.MEMBER)
        task = TaskFactory(board=board, column=todo, created_by=member)

        client = authed_client(owner)
        response = client.delete(reverse("task-detail", kwargs={"pk": task.pk}))
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestTaskFiltering:
    def test_filter_by_column_assignee_and_priority(self):
        owner, workspace, board, todo, in_progress = make_board_with_columns()
        assignee = UserFactory()
        MembershipFactory(workspace=workspace, user=assignee, role=Membership.Role.MEMBER)

        TaskFactory(board=board, column=todo, created_by=owner, priority=Task.Priority.LOW)
        target = TaskFactory(
            board=board,
            column=in_progress,
            created_by=owner,
            assignee=assignee,
            priority=Task.Priority.HIGH,
        )

        client = authed_client(owner)
        response = client.get(
            reverse("task-list"),
            {"column": in_progress.id, "assignee": assignee.id, "priority": "high"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == target.id

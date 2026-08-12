import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from notifications.models import Notification
from users.factories import UserFactory
from workspaces.factories import MembershipFactory, WorkspaceFactory
from workspaces.models import Membership

from .factories import BoardFactory, ColumnFactory, TaskFactory
from .models import Comment

pytestmark = pytest.mark.django_db


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_task_with_assignee():
    owner = UserFactory()
    workspace = WorkspaceFactory(owner=owner)
    MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
    assignee = UserFactory()
    MembershipFactory(workspace=workspace, user=assignee, role=Membership.Role.MEMBER)
    board = BoardFactory(workspace=workspace, created_by=owner)
    column = ColumnFactory(board=board, name="To Do", position=0)
    task = TaskFactory(board=board, column=column, created_by=owner, assignee=assignee)
    return owner, workspace, task, assignee


class TestComments:
    def test_create_comment_notifies_assignee(self):
        owner, workspace, task, assignee = make_task_with_assignee()
        client = authed_client(owner)
        response = client.post(
            reverse("task-comments", kwargs={"pk": task.pk}), {"body": "Looks good to me."}
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert Comment.objects.filter(task=task, body="Looks good to me.").exists()
        assert Notification.objects.filter(recipient=assignee, task=task).exists()

    def test_assignee_commenting_on_own_task_does_not_self_notify(self):
        owner, workspace, task, assignee = make_task_with_assignee()
        client = authed_client(assignee)
        response = client.post(
            reverse("task-comments", kwargs={"pk": task.pk}), {"body": "On it."}
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert not Notification.objects.filter(recipient=assignee, task=task).exists()

    def test_list_comments_for_task(self):
        owner, workspace, task, assignee = make_task_with_assignee()
        client = authed_client(owner)
        client.post(reverse("task-comments", kwargs={"pk": task.pk}), {"body": "First"})
        client.post(reverse("task-comments", kwargs={"pk": task.pk}), {"body": "Second"})

        response = client.get(reverse("task-comments", kwargs={"pk": task.pk}))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_non_member_cannot_comment(self):
        owner, workspace, task, assignee = make_task_with_assignee()
        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.post(
            reverse("task-comments", kwargs={"pk": task.pk}), {"body": "Sneaky comment"}
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

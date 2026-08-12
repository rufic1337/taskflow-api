import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.factories import UserFactory

from .factories import MembershipFactory, WorkspaceFactory
from .models import Membership, Workspace

pytestmark = pytest.mark.django_db


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestWorkspaceCreate:
    def test_creating_workspace_makes_creator_owner(self):
        user = UserFactory()
        client = authed_client(user)
        response = client.post(reverse("workspace-list"), {"name": "Acme Co"})
        assert response.status_code == status.HTTP_201_CREATED

        workspace = Workspace.objects.get(name="Acme Co")
        assert workspace.owner == user
        membership = Membership.objects.get(workspace=workspace, user=user)
        assert membership.role == Membership.Role.OWNER


class TestWorkspaceVisibility:
    def test_non_member_cannot_list_workspace(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)

        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.get(reverse("workspace-list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_non_member_cannot_view_workspace_detail(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)

        outsider = UserFactory()
        client = authed_client(outsider)
        response = client.get(reverse("workspace-detail", kwargs={"pk": workspace.pk}))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceInvite:
    def test_owner_can_invite_existing_user(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
        invitee = UserFactory(email="invitee@example.com")

        client = authed_client(owner)
        response = client.post(
            reverse("workspace-invite", kwargs={"pk": workspace.pk}), {"email": invitee.email}
        )
        assert response.status_code == status.HTTP_201_CREATED
        membership = Membership.objects.get(workspace=workspace, user=invitee)
        assert membership.role == Membership.Role.MEMBER

    def test_plain_member_cannot_invite(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
        member = UserFactory()
        MembershipFactory(workspace=workspace, user=member, role=Membership.Role.MEMBER)
        invitee = UserFactory(email="invitee2@example.com")

        client = authed_client(member)
        response = client.post(
            reverse("workspace-invite", kwargs={"pk": workspace.pk}), {"email": invitee.email}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invite_unknown_email_fails(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)

        client = authed_client(owner)
        response = client.post(
            reverse("workspace-invite", kwargs={"pk": workspace.pk}),
            {"email": "nobody@example.com"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWorkspaceMembership:
    def test_cannot_remove_owner(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)

        client = authed_client(owner)
        response = client.delete(
            reverse("workspace-remove-member", kwargs={"pk": workspace.pk, "user_id": owner.pk})
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Membership.objects.filter(workspace=workspace, user=owner).exists()

    def test_admin_can_remove_member(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
        member = UserFactory()
        MembershipFactory(workspace=workspace, user=member, role=Membership.Role.MEMBER)

        client = authed_client(owner)
        response = client.delete(
            reverse("workspace-remove-member", kwargs={"pk": workspace.pk, "user_id": member.pk})
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Membership.objects.filter(workspace=workspace, user=member).exists()

    def test_non_owner_member_can_leave(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)
        member = UserFactory()
        MembershipFactory(workspace=workspace, user=member, role=Membership.Role.MEMBER)

        client = authed_client(member)
        response = client.post(reverse("workspace-leave", kwargs={"pk": workspace.pk}))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Membership.objects.filter(workspace=workspace, user=member).exists()

    def test_owner_cannot_leave(self):
        owner = UserFactory()
        workspace = WorkspaceFactory(owner=owner)
        MembershipFactory(workspace=workspace, user=owner, role=Membership.Role.OWNER)

        client = authed_client(owner)
        response = client.post(reverse("workspace-leave", kwargs={"pk": workspace.pk}))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

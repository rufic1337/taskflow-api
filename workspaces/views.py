from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import User

from .models import Membership, Workspace
from .permissions import IsWorkspaceAdminOrOwner, IsWorkspaceMember
from .serializers import (
    InviteSerializer,
    MembershipSerializer,
    WorkspaceDetailSerializer,
    WorkspaceListSerializer,
)


class WorkspaceViewSet(viewsets.ModelViewSet):
    queryset = Workspace.objects.none()  # placeholder for schema generation; see get_queryset
    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        return (
            Workspace.objects.filter(memberships__user=self.request.user)
            .distinct()
            .select_related("owner")
            .prefetch_related("memberships__user")
            .annotate(member_count=Count("memberships", distinct=True))
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return WorkspaceListSerializer
        return WorkspaceDetailSerializer

    def get_permissions(self):
        if self.action in ("invite", "remove_member", "update", "partial_update", "destroy"):
            permission_classes = [permissions.IsAuthenticated, IsWorkspaceAdminOrOwner]
        else:
            permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
        return [permission_class() for permission_class in permission_classes]

    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        Membership.objects.create(
            workspace=workspace, user=self.request.user, role=Membership.Role.OWNER
        )

    @action(detail=True, methods=["post"])
    def invite(self, request, pk=None):
        workspace = self.get_object()
        serializer = InviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()
        if user is None:
            return Response(
                {"email": "No user with this email exists."}, status=status.HTTP_400_BAD_REQUEST
            )

        membership, created = Membership.objects.get_or_create(
            workspace=workspace, user=user, defaults={"role": Membership.Role.MEMBER}
        )
        if not created:
            return Response(
                {"email": "User is already a member of this workspace."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        workspace = self.get_object()
        membership = get_object_or_404(Membership, workspace=workspace, user=request.user)
        if membership.role == Membership.Role.OWNER:
            return Response(
                {"detail": "The workspace owner cannot leave without transferring ownership first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, pk=None, user_id=None):
        workspace = self.get_object()
        membership = get_object_or_404(Membership, workspace=workspace, user_id=user_id)
        if membership.role == Membership.Role.OWNER:
            return Response(
                {"detail": "Cannot remove the workspace owner."}, status=status.HTTP_400_BAD_REQUEST
            )
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

from rest_framework import permissions

from .models import Membership


class IsWorkspaceMember(permissions.BasePermission):
    """Grants access to any user with a Membership on the target workspace."""

    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(workspace=obj, user=request.user).exists()


class IsWorkspaceAdminOrOwner(permissions.BasePermission):
    """Grants access only to workspace members with role owner or admin."""

    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            workspace=obj,
            user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        ).exists()

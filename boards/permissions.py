from rest_framework import permissions

from workspaces.models import Membership

from .models import Board, Comment, Task


def _workspace_for(obj):
    """Resolve the owning Workspace for a Board, Task or Comment instance."""
    if isinstance(obj, Board):
        return obj.workspace
    if isinstance(obj, Task):
        return obj.board.workspace
    if isinstance(obj, Comment):
        return obj.task.board.workspace
    if hasattr(obj, "workspace"):
        return obj.workspace
    if hasattr(obj, "board"):
        return obj.board.workspace
    if hasattr(obj, "task"):
        return obj.task.board.workspace
    raise AttributeError(f"Cannot resolve a workspace for {obj!r}")


class IsBoardWorkspaceMember(permissions.BasePermission):
    """Grants access to any member of the object's workspace (Board, Task or Comment)."""

    def has_object_permission(self, request, view, obj):
        workspace = _workspace_for(obj)
        return Membership.objects.filter(workspace=workspace, user=request.user).exists()


class IsOwnerAdminOrCreator(permissions.BasePermission):
    """
    Restricts DELETE to the object's creator/author, or a workspace owner/admin.
    All other methods are left to be handled by other permission classes.
    """

    def has_object_permission(self, request, view, obj):
        if request.method != "DELETE":
            return True

        workspace = _workspace_for(obj)
        is_admin_or_owner = Membership.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        ).exists()
        if is_admin_or_owner:
            return True

        creator_id = getattr(obj, "created_by_id", None)
        if creator_id is None:
            creator_id = getattr(obj, "author_id", None)
        return creator_id == request.user.id

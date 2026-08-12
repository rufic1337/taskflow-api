from rest_framework import serializers

from users.models import User
from users.serializers import UserSerializer
from workspaces.models import Membership

from .models import Board, Column, Comment, Task


class WorkspaceMembershipValidationMixin:
    """Ensures the requesting user is a member of the target workspace on write."""

    def validate_workspace(self, workspace):
        request = self.context["request"]
        if not Membership.objects.filter(workspace=workspace, user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this workspace.")
        return workspace


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ["id", "board", "name", "position"]
        read_only_fields = ["board"]


class BoardListSerializer(WorkspaceMembershipValidationMixin, serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Board
        fields = ["id", "workspace", "name", "created_by", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class BoardDetailSerializer(WorkspaceMembershipValidationMixin, serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ["id", "workspace", "name", "created_by", "columns", "created_at"]
        read_only_fields = ["created_by", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        source="assignee",
        queryset=User.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "board", "column", "title", "description",
            "assignee", "assignee_id", "created_by", "priority",
            "due_date", "position", "created_at", "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate_board(self, board):
        request = self.context["request"]
        if not Membership.objects.filter(workspace=board.workspace, user=request.user).exists():
            raise serializers.ValidationError("You are not a member of this board's workspace.")
        return board

    def validate(self, attrs):
        board = attrs.get("board") or getattr(self.instance, "board", None)
        column = attrs.get("column") or getattr(self.instance, "column", None)
        if board and column and column.board_id != board.id:
            raise serializers.ValidationError({"column": "Column does not belong to the specified board."})
        return attrs


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "task", "author", "body", "created_at"]
        read_only_fields = ["task", "author", "created_at"]

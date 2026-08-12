from django.db import transaction
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from notifications.models import Notification
from notifications.tasks import send_assignment_email, send_comment_email
from realtime.utils import broadcast_board_event

from .filters import BoardFilter, TaskFilter
from .models import Board, Column, Task
from .permissions import IsBoardWorkspaceMember, IsOwnerAdminOrCreator
from .serializers import (
    BoardDetailSerializer,
    BoardListSerializer,
    ColumnSerializer,
    CommentSerializer,
    TaskSerializer,
)

DEFAULT_COLUMNS = ["To Do", "In Progress", "Done"]


class BoardViewSet(viewsets.ModelViewSet):
    queryset = Board.objects.none()  # placeholder for schema generation; see get_queryset
    permission_classes = [permissions.IsAuthenticated, IsBoardWorkspaceMember]
    filterset_class = BoardFilter

    def get_queryset(self):
        return (
            Board.objects.filter(workspace__memberships__user=self.request.user)
            .distinct()
            .select_related("workspace", "created_by")
            .prefetch_related("columns")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return BoardListSerializer
        return BoardDetailSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        board = serializer.save(created_by=self.request.user)
        for position, name in enumerate(DEFAULT_COLUMNS):
            Column.objects.create(board=board, name=name, position=position)

    @action(detail=True, methods=["get", "post"], url_path="columns")
    def columns(self, request, pk=None):
        board = self.get_object()
        if request.method == "GET":
            return Response(ColumnSerializer(board.columns.all(), many=True).data)

        serializer = ColumnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(board=board)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.none()  # placeholder for schema generation; see get_queryset
    permission_classes = [permissions.IsAuthenticated, IsBoardWorkspaceMember, IsOwnerAdminOrCreator]
    serializer_class = TaskSerializer
    filterset_class = TaskFilter

    def get_queryset(self):
        return (
            Task.objects.filter(board__workspace__memberships__user=self.request.user)
            .distinct()
            .select_related("board", "column", "assignee", "created_by")
            .order_by("position", "id")
        )

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        if task.assignee_id:
            self._notify_assignment(task)
        broadcast_board_event(task.board_id, "task.created", TaskSerializer(task).data)

    def perform_update(self, serializer):
        previous_assignee_id = serializer.instance.assignee_id
        task = serializer.save()
        if task.assignee_id and task.assignee_id != previous_assignee_id:
            self._notify_assignment(task)
        broadcast_board_event(task.board_id, "task.updated", TaskSerializer(task).data)

    def perform_destroy(self, instance):
        board_id = instance.board_id
        task_id = instance.id
        instance.delete()
        broadcast_board_event(board_id, "task.deleted", {"id": task_id})

    @staticmethod
    def _notify_assignment(task):
        send_assignment_email.delay(task.id)
        Notification.objects.create(
            recipient=task.assignee, verb="assigned you to a task", task=task
        )

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request, pk=None):
        task = self.get_object()

        if request.method == "GET":
            queryset = task.comments.select_related("author").all()
            return Response(CommentSerializer(queryset, many=True).data)

        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(task=task, author=request.user)

        send_comment_email.delay(comment.id)
        if task.assignee_id and task.assignee_id != request.user.id:
            Notification.objects.create(
                recipient=task.assignee, verb="commented on your task", task=task
            )
        broadcast_board_event(task.board_id, "comment.created", CommentSerializer(comment).data)

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

import django_filters

from .models import Board, Task


class BoardFilter(django_filters.FilterSet):
    class Meta:
        model = Board
        fields = ["workspace"]


class TaskFilter(django_filters.FilterSet):
    class Meta:
        model = Task
        fields = ["board", "column", "assignee", "priority"]

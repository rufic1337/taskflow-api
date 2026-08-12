import factory

from users.factories import UserFactory
from workspaces.factories import WorkspaceFactory

from .models import Board, Column, Comment, Task


class BoardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Board

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Board {n}")
    created_by = factory.SubFactory(UserFactory)


class ColumnFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Column

    board = factory.SubFactory(BoardFactory)
    name = factory.Sequence(lambda n: f"Column {n}")
    position = factory.Sequence(lambda n: n)


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task

    board = factory.SubFactory(BoardFactory)
    column = factory.SubFactory(ColumnFactory, board=factory.SelfAttribute("..board"))
    title = factory.Sequence(lambda n: f"Task {n}")
    created_by = factory.SubFactory(UserFactory)
    priority = Task.Priority.MEDIUM


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    task = factory.SubFactory(TaskFactory)
    author = factory.SubFactory(UserFactory)
    body = factory.Faker("sentence")

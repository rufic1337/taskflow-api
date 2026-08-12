from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from boards.models import Board, Column, Comment, Task
from notifications.models import Notification
from users.models import User
from workspaces.models import Membership, Workspace

DEMO_USERS = [
    ("demo@example.com", "Demo", "User"),
    ("alice@example.com", "Alice", "Nguyen"),
    ("bob@example.com", "Bob", "Martinez"),
    ("carol@example.com", "Carol", "Singh"),
]

TASKS = [
    ("Draft launch announcement", "medium", "To Do", 0),
    ("Finalize pricing page copy", "high", "To Do", 3),
    ("Set up analytics tracking", "low", "To Do", None),
    ("Record product demo video", "medium", "To Do", 7),
    ("Design email campaign", "high", "In Progress", 2),
    ("QA the signup flow", "high", "In Progress", 1),
    ("Write API documentation", "medium", "In Progress", 5),
    ("Prepare launch day social posts", "low", "Done", -1),
    ("Set up status page", "low", "Done", -3),
    ("Configure staging environment", "medium", "Done", -5),
]

COMMENTS = [
    "Let's sync on this tomorrow.",
    "I pushed an update, can you take a look?",
    "Blocked on design review, following up.",
    "Looks good, shipping this.",
]


class Command(BaseCommand):
    help = "Populate the database with a demo workspace, board, tasks and comments."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete existing demo data first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Comment.objects.all().delete()
            Notification.objects.all().delete()
            Task.objects.all().delete()
            Column.objects.all().delete()
            Board.objects.all().delete()
            Membership.objects.all().delete()
            Workspace.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.WARNING("Cleared existing demo data."))

        users = {}
        for email, first_name, last_name in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=email, defaults={"first_name": first_name, "last_name": last_name}
            )
            if created:
                user.set_password("demopass123")
                user.save()
            users[email] = user

        demo_user = users["demo@example.com"]
        other_users = [users[email] for email, *_ in DEMO_USERS[1:]]

        workspace, _ = Workspace.objects.get_or_create(
            name="Demo Workspace", defaults={"owner": demo_user}
        )
        Membership.objects.get_or_create(
            workspace=workspace, user=demo_user, defaults={"role": Membership.Role.OWNER}
        )
        for user in other_users:
            Membership.objects.get_or_create(
                workspace=workspace, user=user, defaults={"role": Membership.Role.MEMBER}
            )

        board, _ = Board.objects.get_or_create(
            workspace=workspace, name="Product Launch", defaults={"created_by": demo_user}
        )

        columns = {}
        for position, name in enumerate(["To Do", "In Progress", "Done"]):
            columns[name], _ = Column.objects.get_or_create(
                board=board, name=name, defaults={"position": position}
            )

        today = timezone.localdate()
        assignable_users = [demo_user, *other_users]
        tasks = []
        for index, (title, priority, column_name, due_offset) in enumerate(TASKS):
            due_date = today + timedelta(days=due_offset) if due_offset is not None else None
            task, _ = Task.objects.get_or_create(
                board=board,
                title=title,
                defaults={
                    "column": columns[column_name],
                    "description": f"Demo task: {title.lower()}.",
                    "created_by": demo_user,
                    "assignee": assignable_users[index % len(assignable_users)],
                    "priority": priority,
                    "due_date": due_date,
                    "position": index,
                },
            )
            tasks.append(task)

        # Deterministic (not random) selection so repeated runs stay idempotent.
        for index in range(min(len(COMMENTS), len(tasks))):
            Comment.objects.get_or_create(
                task=tasks[index],
                author=assignable_users[index % len(assignable_users)],
                body=COMMENTS[index],
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} users, 1 workspace, 1 board, {len(tasks)} tasks. "
            f"Demo login: demo@example.com / demopass123"
        ))

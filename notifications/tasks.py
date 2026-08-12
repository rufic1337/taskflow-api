from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_assignment_email(task_id):
    from boards.models import Task

    task = Task.objects.select_related("assignee", "board").filter(id=task_id).first()
    if not task or not task.assignee:
        return
    send_mail(
        subject=f"You've been assigned: {task.title}",
        message=f"You were assigned to '{task.title}' on board '{task.board.name}'.",
        from_email=None,
        recipient_list=[task.assignee.email],
        fail_silently=True,
    )


@shared_task
def send_comment_email(comment_id):
    from boards.models import Comment

    comment = (
        Comment.objects.select_related("task__assignee", "task__board", "author")
        .filter(id=comment_id)
        .first()
    )
    if not comment:
        return
    task = comment.task
    if not task.assignee or task.assignee_id == comment.author_id:
        return
    send_mail(
        subject=f"New comment on: {task.title}",
        message=(
            f"{comment.author.email} commented on '{task.title}' "
            f"(board '{task.board.name}'): {comment.body}"
        ),
        from_email=None,
        recipient_list=[task.assignee.email],
        fail_silently=True,
    )

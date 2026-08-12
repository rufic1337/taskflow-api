import factory

from users.factories import UserFactory

from .models import Notification


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    recipient = factory.SubFactory(UserFactory)
    verb = "assigned you to a task"
    task = None

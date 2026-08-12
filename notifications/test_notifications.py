import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.factories import UserFactory

from .factories import NotificationFactory
from .models import Notification

pytestmark = pytest.mark.django_db


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class TestNotificationList:
    def test_user_only_sees_own_notifications(self):
        user_a = UserFactory()
        user_b = UserFactory()
        NotificationFactory(recipient=user_a, verb="assigned you to a task")
        NotificationFactory(recipient=user_b, verb="assigned you to a task")

        client = authed_client(user_a)
        response = client.get(reverse("notification-list"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1


class TestMarkRead:
    def test_mark_read_sets_is_read(self):
        user = UserFactory()
        notification = NotificationFactory(recipient=user, is_read=False)

        client = authed_client(user)
        response = client.post(reverse("notification-mark-read", kwargs={"pk": notification.pk}))
        assert response.status_code == status.HTTP_200_OK
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_cannot_mark_read_someone_elses_notification(self):
        user = UserFactory()
        other = UserFactory()
        notification = NotificationFactory(recipient=other, is_read=False)

        client = authed_client(user)
        response = client.post(reverse("notification-mark-read", kwargs={"pk": notification.pk}))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mark_all_read(self):
        user = UserFactory()
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=False)

        client = authed_client(user)
        response = client.post(reverse("notification-mark-all-read"))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0

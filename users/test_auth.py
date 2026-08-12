import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .factories import UserFactory
from .models import User

pytestmark = pytest.mark.django_db


class TestRegistration:
    def test_register_creates_user(self):
        client = APIClient()
        response = client.post(
            reverse("register"),
            {"email": "new@example.com", "password": "StrongPass123!", "first_name": "New"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert User.objects.filter(email="new@example.com").exists()
        assert "password" not in response.data

    def test_register_rejects_weak_password(self):
        client = APIClient()
        response = client.post(
            reverse("register"), {"email": "weak@example.com", "password": "123"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_rejects_duplicate_email(self):
        UserFactory(email="dup@example.com")
        client = APIClient()
        response = client.post(
            reverse("register"), {"email": "dup@example.com", "password": "StrongPass123!"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogin:
    def test_login_returns_tokens(self):
        UserFactory(email="login@example.com", password="StrongPass123!")
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"email": "login@example.com", "password": "StrongPass123!"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data and "refresh" in response.data

    def test_login_rejects_wrong_password(self):
        UserFactory(email="login2@example.com", password="StrongPass123!")
        client = APIClient()
        response = client.post(
            reverse("token_obtain_pair"),
            {"email": "login2@example.com", "password": "wrong"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestMe:
    def test_me_requires_auth(self):
        client = APIClient()
        response = client.get(reverse("me"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_current_user(self):
        user = UserFactory(email="me@example.com")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(reverse("me"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "me@example.com"

    def test_me_patch_updates_current_user(self):
        user = UserFactory(email="patchme@example.com")
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(reverse("me"), {"first_name": "Patched"})
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == "Patched"

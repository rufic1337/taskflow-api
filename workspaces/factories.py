import factory

from users.factories import UserFactory

from .models import Membership, Workspace


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Sequence(lambda n: f"Workspace {n}")
    owner = factory.SubFactory(UserFactory)


class MembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Membership
        django_get_or_create = ("workspace", "user")

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = Membership.Role.MEMBER

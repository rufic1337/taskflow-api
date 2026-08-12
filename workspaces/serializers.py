from rest_framework import serializers

from users.serializers import UserSerializer

from .models import Membership, Workspace


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "role", "joined_at"]


class WorkspaceListSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Workspace
        fields = ["id", "name", "owner", "member_count", "created_at"]


class WorkspaceDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "owner", "members", "created_at"]
        read_only_fields = ["owner", "created_at"]


class InviteSerializer(serializers.Serializer):
    email = serializers.EmailField()

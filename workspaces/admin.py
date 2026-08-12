from django.contrib import admin

from .models import Membership, Workspace


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name", "owner__email"]
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["workspace", "user", "role", "joined_at"]
    list_filter = ["role"]
    search_fields = ["workspace__name", "user__email"]

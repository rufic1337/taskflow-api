from django.contrib import admin

from .models import Board, Column, Comment, Task


class ColumnInline(admin.TabularInline):
    model = Column
    extra = 0


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ["name", "workspace", "created_by", "created_at"]
    search_fields = ["name", "workspace__name"]
    inlines = [ColumnInline]


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ["name", "board", "position"]
    list_filter = ["board"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "board", "column", "assignee", "priority", "due_date"]
    list_filter = ["priority", "board"]
    search_fields = ["title", "description"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["task", "author", "created_at"]
    search_fields = ["body"]
